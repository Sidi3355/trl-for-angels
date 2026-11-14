// Terms of use (DRAFT). Keep in step with how the app works (see the privacy notice and app/README.md).
import type { Metadata } from "next";
import Link from "next/link";

import { Clause, DraftBanner, LEGAL_UPDATED } from "@/components/Legal";
import { Page, PageHeader, linkClass } from "@/components/ui";

export const metadata: Metadata = { title: "Terms (draft)" };

export default function TermsPage() {
  return (
    <Page>
      <PageHeader eyebrow={`Draft · updated ${LEGAL_UPDATED}`} title="Terms of use" subtitle="The rules for using the Halomark prototype, in plain words." />
      <DraftBanner />

      <div className="mt-8">
        <Clause n={1} title="What Halomark is">
          <p>
            A screening aid for angel investors. It researches a founder&apos;s public background and estimates the odds of a large outcome, as a first pass before your own judgement.
          </p>
          <p>
            <strong className="font-semibold text-ink">It is not investment, financial, legal or tax advice.</strong> Every decision to meet, invest or pass is yours.
          </p>
        </Clause>

        <Clause n={2} title="How far to trust it">
          <ul>
            <li>The odds are estimates from a model trained mostly on generated data. No real-world accuracy is claimed.</li>
            <li>In this prototype the scores are examples until the trained model is plugged in.</li>
            <li>The research agent can miss facts or get them wrong. Check the linked sources before relying on anything.</li>
          </ul>
        </Clause>

        <Clause n={3} title="Using it fairly">
          <ul>
            <li>Screen people only for a genuine investment purpose, using public information.</li>
            <li>Don&apos;t use Halomark to harass anyone, or for decisions about employment, credit, housing or anything other than an early investment screen.</li>
            <li>Don&apos;t paste in private information you aren&apos;t allowed to share.</li>
            <li>Don&apos;t try to break, overload or copy the service.</li>
          </ul>
        </Clause>

        <Clause n={4} title="Your content">
          <p>
            Your notes, recordings and profile stay yours. Halomark uses them only to provide the service, as the{" "}
            <Link href="/privacy" className={linkClass}>
              privacy notice
            </Link>{" "}
            describes, and keeps nothing on its servers after your session.
          </p>
        </Clause>

        <Clause n={5} title="The prototype">
          <ul>
            <li>Halomark may change, pause or stop at any time, without notice. There is no service level.</li>
            <li>
              Every feature is free while it&apos;s a prototype. The{" "}
              <Link href="/plans" className={linkClass}>
                plans
              </Link>{" "}
              are a preview: nothing can be bought, and nothing is charged.
            </li>
          </ul>
        </Clause>

        <Clause n={6} title="Responsibility">
          <p>
            Halomark is provided as it is. As far as the law allows, its makers aren&apos;t responsible for decisions made using it, or for losses that follow from them. [Wording to be reviewed.]
          </p>
        </Clause>

        <Clause n={7} title="Still to be decided">
          <ul>
            <li>Who provides Halomark, a contact address, and the governing law.</li>
            <li>Age limits, account rules for paid plans, and how changes to these terms are announced.</li>
          </ul>
        </Clause>
      </div>
    </Page>
  );
}
