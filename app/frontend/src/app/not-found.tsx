import Link from "next/link";

import { Page, PageHeader } from "@/components/ui";

export default function NotFound() {
  return (
    <Page>
      <div className="pt-16">
        <PageHeader title="Not found" subtitle="This page doesn't exist, or the memo has expired. Memos are kept only for a while." />
        <Link href="/" className="text-[16px] font-semibold text-accent hover:text-accent-hover">
          Back to Deals
        </Link>
      </div>
    </Page>
  );
}
