import { createPage } from "@/lib/site-page";

const page = createPage('/share/summary.html');

export const generateMetadata = page.generateMetadata;
export default page.Page;
