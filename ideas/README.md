# 文件靈感庫

The `/ideas/` tool follows the site's shared `assets/base.css`, fonts, navigation, buttons, cards and iris palette. `assets/site.js` adds it to the homepage tools shelf.

The public starter contains six explicitly labelled example documents. Personal creator plans, source Word files, local paths and the earlier private vault are not bundled. The existing `collection.json` format can be imported manually; filesystem metadata and untrusted download URLs are discarded.

## Capabilities

- Search document content and titles; read verbatim excerpts and highlighted source text.
- Import MD/TXT, DOCX body/table text, text-bearing PDF, or validated JSON backups.
- Add a note, retain source links, explore actual topic classifications.
- Persist the collection and imported original files in IndexedDB, only on that origin/device. A failed import or storage transaction does not replace the current collection.
- Export JSON for reimport, or an Obsidian-compatible Markdown ZIP. Neither export includes original binary documents; users should retain those separately.

No AI inference, embeddings, OCR, server storage, accounts or document uploads. PDF page markers refer to source pages; line highlights refer to extracted text. Image-only/scanned PDFs and password-protected PDFs fail with a useful message. Word images, annotations and complex layout are not preserved in the extracted text.

Limits: 20 files per import, 10 MB per file, 50 MB per batch, 100 PDF pages, 100 source documents, 600 excerpts and 2 million source characters. The graph shows up to 40 relevant excerpts, with the actual displayed count. Search results are paginated locally. This is intended for selected working files, not a whole-disk index.

## Dependencies

Reuses the existing bundled `assets/pdf.min.js` and worker. DOCX archive extraction and Markdown ZIP exports use fflate 0.8.3, vendored from its npm registry tarball after SHA-512 integrity verification. MIT license: `assets/vendor/fflate-LICENSE.txt`. No package-manager or build-system changes.

## Verification

Run from repository root:

```sh
node --test tests/ideas.test.mjs
node --check ideas/app.mjs
node --check ideas/files.mjs
```

Checks cover source matching, unrelated queries, append/import behaviour, excerpt integrity, metadata stripping, file limits, DOCX archive entry selection, actual PDF text/page extraction, image-only PDF rejection and local asset links. The PDF parser's Node test uses its main-thread fallback and may print standard-font warnings; text assertions must still pass.

Browser visual review, IndexedDB persistence/reload, full DOM-based Word parsing, downloads, and WebMCP execution still require an available browser session. The current browser inspection was unavailable because its admin-enforced policy could not be verified; this was not bypassed.

No build is required. Serve the repo root, then open `/ideas/`. Publishing follows the repository's existing deployment, not a separate site.
