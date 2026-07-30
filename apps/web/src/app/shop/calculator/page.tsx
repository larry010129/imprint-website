import { createPage } from "@/lib/site-page";

const page = createPage('/shop/calculator/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
