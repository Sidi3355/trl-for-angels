import Link from "next/link";

import { Page } from "@/components/ui";

export default function NotFound() {
  return (
    <Page>
      <h1 className="mt-16 text-[28px] font-bold">Not found</h1>
      <p className="mt-2 text-[15px] text-muted">This page doesn&apos;t exist.</p>
      <Link href="/" className="mt-6 inline-block text-[17px] text-accent">Screen a founder</Link>
    </Page>
  );
}
