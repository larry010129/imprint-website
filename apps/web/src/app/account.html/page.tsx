import { createPage } from "@/lib/site-page";

const page = createPage('/account.html');

export const generateMetadata = page.generateMetadata;
export default page.Page;
