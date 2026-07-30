import { createPage } from "@/lib/site-page";

const page = createPage('/jewelry/earrings/');

export const generateMetadata = page.generateMetadata;
export default page.Page;
