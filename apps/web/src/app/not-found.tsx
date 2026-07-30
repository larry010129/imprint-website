import { createPage } from "@/lib/site-page";

const page = createPage("/404.html");

export default async function NotFound() {
  return page.Page({});
}
