import { createPage } from "@/lib/site-page";

const page = createPage("/404.html");

export const generateMetadata = page.generateMetadata;
export default page.Page;
