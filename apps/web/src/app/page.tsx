import { createPage } from "@/lib/site-page";

const page = createPage('/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
