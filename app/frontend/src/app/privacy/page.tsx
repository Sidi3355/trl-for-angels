// Privacy notice (DRAFT). It must match what the app actually does: check it against app/README.md and
// app/backend whenever data handling changes (storage, third parties, retention, logs).
import type { Metadata } from "next";
import Link from "next/link";

import { Clause, DraftBanner, LEGAL_UPDATED } from "@/components/Legal";
import { Page, PageHeader, linkClass } from "@/components/ui";

export const metadata: Metadata = { title: "Privacy (draft)" };

export default function PrivacyPage() {
  return (
    <Page>
      <PageHeader eyebrow={`Draft · updated ${LEGAL_UPDATED}`} title="Privacy" subtitle="Halomark is built to keep as little as possible: nothing on our servers after your session, and your profile only on your device." />
      <DraftBanner />

      <div className="mt-8">
        <Clause n={1} title="The short version">
          <ul>
            <li>Halomark researches founders you name, using public information from before they founded their company.</li>
            <li>Screenings, memos and notes are held in our server&apos;s memory only, and deleted within about two hours. There is no database.</li>
            <li>Your profile and settings are saved only in this browser, on this device. They are not sent to our servers.</li>
            <li>To do its job, Halomark sends some data to the services listed in section 5.</li>
          </ul>
        </Clause>

        <Clause n={2} title="About the founders you screen">
          <p>
            When you screen someone, Halomark uses their name, any links you give (such as a LinkedIn profile or website), and facts found in public sources from before their company was
            founded: their background, education, jobs, earlier companies and exits. It doesn&apos;t look for private information, contact details or anything about their life outside work.
          </p>
          <p>
            Before scoring, the facts are written into an anonymised profile: no names of people, companies, universities or products, no exact dates or places. The scoring model only ever sees
            that profile. Founders aren&apos;t notified that they were screened.
          </p>
        </Clause>

        <Clause n={3} title="About you">
          <ul>
            <li>
              <strong className="font-semibold text-ink">Your profile</strong> (name, optional email, sectors, stage, cheque size, geography and default settings) is saved in this browser&apos;s
              storage on this device only. Halomark has no account for you on a server.
            </li>
            <li>
              <strong className="font-semibold text-ink">Your bar</strong> (target, timeline, risk appetite and filters) is saved on this device, and verdicts are worked out in the app itself. It goes to the
              server only when you ask for a notification, so the message can state the verdict at your bar.
            </li>
            <li>
              <strong className="font-semibold text-ink">Your notes</strong> go with the screening and appear in the memo. They are never given to the scoring model. If you fill the form from your notes,
              their text is sent to Claude to pick out facts, which you check.
            </li>
            <li>
              <strong className="font-semibold text-ink">Voice notes</strong> are sent to ElevenLabs to turn into text. Halomark doesn&apos;t keep the recording.
            </li>
            <li>
              <strong className="font-semibold text-ink">Notifications</strong>, if you turn them on: your browser&apos;s push address is kept in memory until the one notification is sent, then forgotten.
            </li>
          </ul>
        </Clause>

        <Clause n={4} title="How long things are kept">
          <ul>
            <li>On our server: screenings, memos, notes and research results are kept in memory for up to about two hours after they finish, or until the server restarts, then deleted.</li>
            <li>
              Server logs, kept by our hosting provider, record technical events (timings, errors, costs). Halomark doesn&apos;t write founder names, notes or profile details to them.
            </li>
            <li>On your device: this session&apos;s founders list until you close the app; your profile and bar until you delete them.</li>
          </ul>
        </Clause>

        <Clause n={5} title="Services that process data for Halomark">
          <ul>
            <li>
              <strong className="font-semibold text-ink">Anthropic (Claude):</strong> searches the web about the founder you name, and sorts notes into the form when you ask.
            </li>
            <li>
              <strong className="font-semibold text-ink">ElevenLabs:</strong> turns voice notes into text.
            </li>
            <li>
              <strong className="font-semibold text-ink">Kev hosting:</strong> the anonymised profile, with no names, is scored by Kev, running on the project owner&apos;s own computer and reached
              through a Cloudflare tunnel. The model itself is stored on Hugging Face. In this prototype the scores are still placeholders.
            </li>
            <li>
              <strong className="font-semibold text-ink">Hosting:</strong> Vercel serves the app&apos;s pages; Railway runs the server.
            </li>
            <li>
              <strong className="font-semibold text-ink">Push services:</strong> Apple, Google or Mozilla deliver notifications to your browser.
            </li>
          </ul>
          <p>Each processes data under its own terms and privacy policy.</p>
        </Clause>

        <Clause n={6} title="Your choices">
          <ul>
            <li>
              Delete everything Halomark keeps on this device with <strong className="font-semibold text-ink">Delete all my data</strong> on the{" "}
              <Link href="/account" className={linkClass}>
                You
              </Link>{" "}
              page.
            </li>
            <li>Switch off web research when screening, to use only what you enter.</li>
            <li>Founders and anyone else can ask about data concerning them at [contact to be added]. As nothing is kept after the session, there is usually nothing left to find or delete.</li>
          </ul>
        </Clause>

        <Clause n={7} title="Still to be decided">
          <ul>
            <li>The legal basis for researching named founders (likely legitimate interests) and the data controller&apos;s details.</li>
            <li>A contact address, international transfers, and whether this notice meets UK GDPR and GDPR as written.</li>
          </ul>
        </Clause>
      </div>
    </Page>
  );
}
