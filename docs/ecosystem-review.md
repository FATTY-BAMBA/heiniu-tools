# HEINIU ecosystem design review

The production homepage was inspected at 1440 × 920 and 390 × 844 on November 18, 2026 (Taipei), with English and Traditional Chinese checked at the mobile width. Desktop and mobile observations are based on rendered pages and inspection of the production-matching source. This is a targeted design and accessibility review.

| Area | Production observation | Redesign |
| --- | --- | --- |
| Typography | The display headline, monospaced labels, card numbering, and badges all compete for attention. Some small, light labels are difficult to read. | A simpler type hierarchy and stronger body contrast. Monospace is reserved for technical context. |
| Layout | The salary mockup and generous hero spacing occupy nearly all of the first desktop viewport. At 390 px, the catalog starts below the first screen in both languages. | A compact feature panel, shorter section leads, and a denser card layout bring the tools closer to the top. |
| Hierarchy | The featured tool looks like a calculator with embedded controls, but the entire panel links to the calculator. Repeated tool tags consume space with little added context. | The folder feature presents a schematic with one clear action. Catalog cards lead with their titles and descriptions. |
| Navigation | Tools, Guides, and Radar disappear from the mobile header while the Instagram CTA remains. The portfolio has no entry point. | Keep all four primary links visible at mobile widths. Put social links and PrimeStride AI in the footer, with portfolio and business links in the creator section. |
| Responsiveness | No horizontal overflow at 390 px. English hero buttons stack while the Chinese buttons share a row. Mobile content takes longer to scan because the cards reserve substantial space for previews. | Allow CTA wrapping and use a compact single-column catalog on narrow screens, two columns at tablet widths, and four on desktop. |
| Motion | Hero entrance effects and hover lift add movement to the main reading path. Shared styles already include reduced-motion rules. | Keep the new pages still and use visual affordances through borders, underlines, and keyboard focus. |
| Usability | Catalog cards are clickable but place decorative previews ahead of titles. The sample token-reduction percentage can read like a measured outcome. | Lead with the task and remove the unsourced percentage and other decorative figures. Add a skip link, visible focus, and larger navigation targets. |
| Localization | The switch persists on the site and changes a substantial amount of copy. Some Chinese accessible names remain in English and some English interface labels remain in Chinese. Child pages use a combination of a curated string dictionary and dedicated bilingual markup. | Author both languages for new page copy and keep the existing language preference and catalog translations. Existing child-page translation coverage varies by route. |

## Content and release scope

- The starting point includes the live File Universe feature and its latest existing fixes, which are ahead of GitHub's default branch.
- The public HEINIU site is the tools and learning entry point. The portfolio explains the design and research behind selected work. PrimeStride AI handles business inquiries through its existing company site.
- The current conversation did not provide the earlier design artifact. The portfolio uses the public Abdoulie Fatty portfolio and its portrait as reference, alongside DOI records for the research. The published findings are phrased qualitatively where the available source lacks a verifiable benchmark. The segmentation demo uses illustrative geometry.
- The review branch is for a Vercel preview. Production promotion requires separate approval.
