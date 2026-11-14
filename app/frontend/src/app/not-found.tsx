import Link from "next/link";

import { Halo, Page, PageHeader, linkClass } from "@/components/ui";

export default function NotFound() {
  return (
    <Page>
      <div className="pt-16">
        <Halo className="mb-6 h-8 w-auto text-ink" />
        <PageHeader title="Not found" subtitle="This page doesn't exist, or the memo has expired. Memos are kept only for a while." />
        <Link href="/" className={linkClass}>
          Back to your founders
        </Link>
      </div>
    </Page>
  );
}
