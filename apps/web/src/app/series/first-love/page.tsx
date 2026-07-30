import { createPage } from "@/lib/site-page";

const page = createPage('/series/first-love/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
