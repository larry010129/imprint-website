"use client";

import { useEffect } from "react";

type Props = {
  className?: string;
  mvcPage?: string | null;
  siteCmsEdit?: boolean;
  cmsPageKey?: string;
  siteRoot?: boolean;
};

/** Mirror Jinja body attrs — MVC + CMS edit scripts read document.body. */
export default function BodyAttrs({
  className,
  mvcPage,
  siteCmsEdit,
  cmsPageKey,
  siteRoot,
}: Props) {
  useEffect(() => {
    const body = document.body;
    const prevClass = body.className;
    const prevMvc = body.getAttribute("data-mvc");
    const prevEdit = body.getAttribute("data-cms-site-edit");
    const prevInline = body.getAttribute("data-cms-inline");
    const prevKey = body.getAttribute("data-cms-page-key");
    const prevRoot = body.getAttribute("data-site-root");

    if (className) body.className = className;
    if (mvcPage) body.setAttribute("data-mvc", mvcPage);
    else body.removeAttribute("data-mvc");
    if (siteCmsEdit) {
      body.setAttribute("data-cms-site-edit", "1");
      body.setAttribute("data-cms-inline", "1");
      if (cmsPageKey) body.setAttribute("data-cms-page-key", cmsPageKey);
    }
    if (siteRoot) body.setAttribute("data-site-root", "");

    return () => {
      body.className = prevClass;
      if (prevMvc) body.setAttribute("data-mvc", prevMvc);
      else body.removeAttribute("data-mvc");
      if (prevEdit) body.setAttribute("data-cms-site-edit", prevEdit);
      else body.removeAttribute("data-cms-site-edit");
      if (prevInline) body.setAttribute("data-cms-inline", prevInline);
      else body.removeAttribute("data-cms-inline");
      if (prevKey) body.setAttribute("data-cms-page-key", prevKey);
      else body.removeAttribute("data-cms-page-key");
      if (prevRoot !== null) body.setAttribute("data-site-root", prevRoot);
      else body.removeAttribute("data-site-root");
    };
  }, [className, mvcPage, siteCmsEdit, cmsPageKey, siteRoot]);

  return null;
}
