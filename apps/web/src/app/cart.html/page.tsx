import { createPage } from "@/lib/site-page";

const page = createPage('/cart.html');

export const generateMetadata = page.generateMetadata;
export default page.Page;
