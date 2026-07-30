import { createPage } from "@/lib/site-page";

const page = createPage('/series/love/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
