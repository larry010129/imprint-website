import { createPage } from "@/lib/site-page";

const page = createPage('/register.html');

export const generateMetadata = page.generateMetadata;
export default page.Page;
