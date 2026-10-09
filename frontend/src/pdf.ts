import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

// pdf.js parses in a web worker so a large file does not freeze the page.
GlobalWorkerOptions.workerSrc = workerUrl;

// Extracted in the browser so the API contract stays plain text. Scanned PDFs have no text layer.
export async function extractPdfText(file: File): Promise<string> {
  const pdf = await getDocument({ data: await file.arrayBuffer() }).promise;
  const pages: string[] = [];
  for (let n = 1; n <= pdf.numPages; n++) {
    const content = await (await pdf.getPage(n)).getTextContent();
    pages.push(content.items.map((item) => ("str" in item ? item.str + (item.hasEOL ? "\n" : "") : "")).join(""));
  }
  return pages.join("\n\n").trim();
}
