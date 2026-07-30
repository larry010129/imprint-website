import { createPage } from "@/lib/site-page";

const page = createPage('/quote-sheet');

export const generateMetadata = page.generateMetadata;
export default page.Page;
