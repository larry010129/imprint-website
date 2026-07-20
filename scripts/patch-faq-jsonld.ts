import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { FAQ_JSON_LD } from "../frontend/src/data/faq-content.ts"

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..")
const faqPath = path.join(root, "app/views/pages/faq.html")
let html = fs.readFileSync(faqPath, "utf8")

const entities = FAQ_JSON_LD.map((q) => ({
  "@type": "Question",
  name: q.name,
  acceptedAnswer: { "@type": "Answer", text: q.text },
}))

const inner = JSON.stringify(entities, null, 4)
  .split("\n")
  .map((line, i) => (i === 0 ? line : `    ${line}`))
  .join("\n")

html = html.replace(
  /"mainEntity":\s*\[[\s\S]*?\]\s*\n\}/,
  `"mainEntity": ${inner}\n}`,
)

fs.writeFileSync(faqPath, html)
console.log(`patched ${entities.length} FAQ JSON-LD entries`)
