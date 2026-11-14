import { MemoView } from "@/components/memo/MemoView";

export default async function MemoPage({ params }: { params: Promise<{ memoId: string }> }) {
  const { memoId } = await params;
  return <MemoView memoId={memoId} />;
}
