import { createPage } from "@/lib/site-page";

const page = createPage('/series/heirloom/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
