import { createPage } from "@/lib/site-page";

const page = createPage('/jewelry/rings/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
