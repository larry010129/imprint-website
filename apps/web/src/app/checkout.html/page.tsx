import { createPage } from "@/lib/site-page";

const page = createPage('/checkout.html');

export const generateMetadata = page.generateMetadata;
export default page.Page;
