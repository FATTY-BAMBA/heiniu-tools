"""Browser regressions for the Stage 2 tool fixes. All transactions and files are synthetic."""
import argparse
import json
import re
import shutil
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from responsive_qa import serve


def pdf_fixture(pages):
    objects = ["<< /Type /Catalog /Pages 2 0 R >>",
               "<< /Type /Pages /Kids [" + " ".join(f"{4+2*i} 0 R" for i in range(len(pages)))
               + f"] /Count {len(pages)} >>",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, line in enumerate(pages):
        stream = f"BT /F1 18 Tf 30 720 Td ({line}) Tj ET" if line else " "
        objects.extend([f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] "
                        f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5+2*i} 0 R >>",
                        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"])
    data = "%PDF-1.4\n"
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n{obj}\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    data += "".join(f"{x:010d} 00000 n \n" for x in offsets)
    data += f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n"
    return {"name": "qa-pages.pdf", "mimeType": "application/pdf", "buffer": data.encode()}


def pdf(page, origin, out):
    page.goto(origin + "/pdf/?lang=en")
    q = page.locator
    expect(q(".lede")).to_contain_text("can use up tokens quickly. Choose specific pages to extract plain text and copy")
    expect(q("#p2")).to_have_attribute("inert", "")
    q("#file").set_input_files(pdf_fixture(["ALPHA first page", "BRAVO second page", "CHARLIE third page"]))
    expect(q("#fpg")).to_have_text("3 pages")
    for token, indices in [("2", [1]), ("3,1,3", [0, 2]), ("3-2", [1, 2]), ("", [0, 1, 2])]:
        q("#range").fill(token)
        q("#go").click()
        expect(q("#p3")).not_to_have_attribute("inert", "")
        value = q("#output").input_value()
        assert [i for i, word in enumerate(["ALPHA", "BRAVO", "CHARLIE"]) if word in value] == indices
        assert value.count("Page ") == (len(indices) if len(indices) > 1 else 0)
    for button in ["copyText", "copyPrompt"]:
        q("#" + button).click()
        copied = page.evaluate("navigator.clipboard.readText()")
        assert (copied == value if button == "copyText" else copied.startswith("Answer my question") and value in copied)
    page.screenshot(path=out / "pdf-text.jpg", type="jpeg", quality=82)
    q("#range").fill("2,99")
    q("#go").click()
    expect(q("#pdfError")).to_have_text("Enter page numbers from 1 to 3.")
    expect(q("#output")).to_have_value("")
    q("[data-all]").focus()
    page.keyboard.press("Enter")
    expect(q("#range")).to_have_value("")
    q("#reset").click()
    q("#file").set_input_files(pdf_fixture(["", ""]))
    expect(q("#fpg")).to_have_text("2 pages")
    q("#go").click()
    expect(q("#scan")).to_be_visible()
    expect(q("#p3")).to_have_attribute("inert", "")
    expect(q("#output")).to_have_value("")
    page.screenshot(path=out / "pdf-empty.jpg", type="jpeg", quality=82)


def universe(page, origin, out):
    page.goto(origin + "/sort/?lang=en")
    q = page.locator
    expect(q("#stage")).to_have_attribute("inert", "")
    q("#cpMain").click()
    assert len(page.evaluate("navigator.clipboard.readText()")) > 250
    for payload, message in [(b"{", "Could not read"), (b'{"files":[]}', "non-empty files array")]:
        q("#pick").set_input_files({"name":"classification.json", "mimeType":"application/json", "buffer":payload})
        expect(page.get_by_role("alert")).to_contain_text(message)
    q("#demo").click()
    expect(q("#heroN")).to_have_text("300")
    q("#bOver").focus()
    page.keyboard.press("m")
    expect(q("#bSound")).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Enter")
    expect(q("#shX")).to_be_focused()
    q("#list button").first.click()
    expect(q("#list .row").first).to_be_visible()
    page.keyboard.press("Escape")
    expect(q("#bOver")).to_be_focused()
    expect(q("#sheet")).to_have_attribute("inert", "")
    q("#stage").focus()
    page.keyboard.press("m")
    expect(q("#bSound")).to_have_attribute("aria-pressed", "false")
    page.keyboard.press("t")
    expect(q("#bTheme")).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("r")
    expect(q("body")).to_have_class(re.compile(r"\brec\b"))
    page.keyboard.press("Escape")
    expect(q("body")).not_to_have_class(re.compile(r"\brec\b"))
    q("#bReplay").click()
    expect(q("#fin")).to_have_class("hud on", timeout=45000)
    q("#bReplay").click()
    expect(q("#fin")).not_to_have_class("hud on")
    q("#bLang").click()
    expect(q("html")).to_have_attribute("lang","zh-Hant")
    expect(q("#bSound")).to_have_text("音效 關")
    q("#bar a").click()
    assert "lang=zh" in page.url
    page.goto(origin + "/sort/?lang=en")
    payload = json.dumps({"source":"QA imports","files":[{"name":"alpha.txt","category":"Invoices"},
              {"name":"beta.pdf","category":"Invoices"},{"name":"gamma.md","needsReview":True}]})
    transfer = page.evaluate_handle("""text => { const data = new DataTransfer();
      data.items.add(new File([text], 'classification.json', {type:'application/json'})); return data; }""", payload)
    q(".dz").dispatch_event("drop", {"dataTransfer":transfer})
    q("#bOver").click()
    expect(q("#shC")).to_have_text("3")
    expect(q("#list")).to_contain_text("Invoices")
    q("#list button").filter(has_text="Invoices").click()
    expect(q("#list .row")).to_have_count(2)
    page.screenshot(path=out / "universe-category.jpg", type="jpeg", quality=82)


def courses(page, origin, out):
    q = page.locator
    page.goto(origin + "/claude-zerotohero/en/?lang=en")
    for lang in ["en", "zh"]:
        if lang == "zh":
            q('.shell-languages [data-lang-choice="zh"]').click()
        for link in q("#toc a").all():
            target = link.get_attribute("href")
            link.click()
            expect(link).to_have_attribute("aria-current", "location")
            assert page.locator(target).count() == 1
        assert float(q("#prog").evaluate("e => e.style.width.replace('%','')")) > 75
        q("#memory .copy").first.click()
        assert page.evaluate("navigator.clipboard.readText()") == q("#memory .prompt pre").first.inner_text().strip()
        for box in q("#weekList input").all():
            box.check()
        expect(q("#weekDone b")).to_have_text("7")
        page.reload()
        expect(q("#weekList input:checked")).to_have_count(7)
        expect(q("#weekDone")).to_have_attribute("role","status")
        q('#toc a[href="#week"]').click()
        page.screenshot(path=out / f"course-{lang}.jpg", type="jpeg", quality=82)
        q("#weekList input").last.uncheck()
        expect(q("#weekDone b")).to_have_text("6")


def salary(page, origin, out):
    page.goto(origin + "/salary/?lang=en")
    q = page.locator
    cases = [(60000, 0, 0, 1, "57,924", "755,093"),
             (28000, 1, 3, 0, "25,591", "307,097"),
             (250000, 3, 6, 1.5, "226,237", "3,089,847"),
             (0, 0, 0, 0, "0", "0")]
    for gross, dependents, voluntary, bonus, monthly, annual in cases:
        q("#salary").click()
        q("#salary").fill(str(gross))
        for group, value in [("dep", dependents), ("self", voluntary), ("bonus", bonus)]:
            selected = q(f"#{group} [data-v='{value}']")
            selected.click()
            expect(selected).to_have_attribute("aria-pressed","true")
        expect(q("#net")).to_have_text(monthly)
        expect(q("#anet")).to_have_text(annual)
    q("#salary").click()
    q("#salary").fill("60000")
    q("summary").click()
    q("#rate_labor").fill("0")
    q("#cap_nhi").fill("10000")
    expect(q("#net")).to_have_text("59,845")
    page.get_by_role("button",name="繁中").click()
    expect(q("#net")).to_have_text("59,845")
    expect(q("#rate_labor")).to_have_value("0")


def spending(page, origin, out):
    page.goto(origin + "/spending/?lang=en")
    q = page.locator
    q("#sample").click()
    expect(q("#rentV")).to_have_text("NT$ 216,000")
    expect(q("#wasteV")).to_have_text("NT$ 228,072")
    q("#stmt").fill("2026/01/01 UBER EATS 100\n2026/01/02 NETFLIX 200")
    q("#analyze").click()
    expect(q("#verdict")).to_contain_text("No rent")
    expect(q("#wasteV")).to_have_text("NT$ 3,600")
    q("#toggleEdit").click()
    q("#amount-delivery").fill("12.50")
    expect(q("#wasteV")).to_have_text("NT$ 2,550")
    q("#stmt").fill("2026/01/31 UBER EATS 100\n2026/02/01 NETFLIX 200")
    q("#analyze").click()
    expect(q("#periodSel")).to_have_value("2")
    expect(q("#wasteV")).to_have_text("NT$ 1,800")
    q("#periodSel").select_option("12")
    expect(q("#wasteV")).to_have_text("NT$ 300")
    for text in ["", "no transaction amount"]:
        q("#stmt").fill(text)
        q("#analyze").click()
        expect(q("#results")).not_to_be_visible()
        expect(page.get_by_role("alert")).to_be_visible()
    q("#sample").click()
    expect(q("#results")).to_be_visible()
    expect(q("#inputError")).not_to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with serve(args.root) as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=shutil.which("google-chrome") or shutil.which("chromium"))
        for test in (pdf, universe, courses, salary, spending):
            context = browser.new_context(permissions=["clipboard-read","clipboard-write"], reduced_motion="reduce")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            test(page, origin, args.out)
            assert not errors, errors
            print("PASS", test.__name__, flush=True)
            context.close()
        browser.close()


if __name__ == "__main__":
    main()
