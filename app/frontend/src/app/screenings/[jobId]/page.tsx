import { Progress } from "@/components/Progress";

export default async function ScreeningPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <Progress jobId={jobId} />;
}
