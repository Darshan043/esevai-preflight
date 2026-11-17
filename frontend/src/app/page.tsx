import Link from "next/link";
import { Suspense } from "react";
import { ClipboardCheck, FileStack, MapPin, MessageSquareText, ShieldCheck, BadgeCheck } from "lucide-react";

import { Disclaimer } from "@/components/Disclaimer";
import { HomeActions } from "@/components/HomeActions";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { SystemStatus } from "@/components/SystemStatus";
import { getRequestLanguage, listServices } from "@/lib/catalog";
import { pickName } from "@/lib/language";

const steps = [
  {
    title: "Pick a service",
    text: "Choose the certificate or service you plan to apply for.",
    Icon: FileStack,
  },
  {
    title: "Upload your documents",
    text: "Add each document from the checklist. Upload opens in the next step.",
    Icon: ClipboardCheck,
  },
  {
    title: "Get your readiness report",
    text: "See what is ready and what still needs a fix before you apply.",
    Icon: ShieldCheck,
  },
];

const reasons = [
  {
    title: "Fewer rejections",
    text: "Catch a missing or unreadable document before the counter does.",
    Icon: BadgeCheck,
  },
  {
    title: "Saves a trip",
    text: "Check the list at home instead of travelling with the wrong papers.",
    Icon: MapPin,
  },
  {
    title: "Plain-language fixes",
    text: "Each problem is explained in everyday words, with a next step.",
    Icon: MessageSquareText,
  },
];

async function SupportedServices() {
  const [language, result] = await Promise.all([getRequestLanguage(), listServices()]);
  if (result.error || result.items.length === 0) {
    return (
      <p className="text-muted">
        <Link href="/services" className="font-semibold text-royal underline-offset-2 hover:underline">
          Open the service list
        </Link>{" "}
        to see what you can prepare.
      </p>
    );
  }

  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {result.items.map((service) => (
        <li key={service.id} className="panel service-card">
          <h3 className="text-lg font-semibold text-navy">{pickName(service, language)}</h3>
          <p className="mt-3 inline-flex rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
            {service.documentCount} required document{service.documentCount === 1 ? "" : "s"}
          </p>
          <Link href={`/services/${service.slug}`} className="btn-secondary mt-4">
            View details
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <>
      <section className="border-b border-line bg-navy text-white">
        <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.35fr_0.85fr] lg:items-center lg:py-14">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-sky uppercase">Independent document pre-check</p>
            <h1 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-5xl">
              Check your documents before you apply
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-sky">
              e-Sevai Pre-Flight helps you prepare a government application before you submit it.
            </p>
            <div className="mt-6">
              <Suspense fallback={<p className="text-sky">Loading account actions...</p>}>
                <HomeActions />
              </Suspense>
            </div>
          </div>
          <aside className="rounded-lg border border-white/70 bg-white p-5 text-ink shadow-sm">
            <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Service desk</p>
            <h2 className="mt-1 text-lg font-semibold text-navy">What you can do today</h2>
            <ol className="mt-4 space-y-3 text-sm leading-6">
              <li className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sky text-xs font-semibold text-navy">1</span>
                Browse the Community Certificate checklist.
              </li>
              <li className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sky text-xs font-semibold text-navy">2</span>
                Start a draft document check after you sign in.
              </li>
              <li className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sky text-xs font-semibold text-navy">3</span>
                Upload and the readiness report open in a later step.
              </li>
            </ol>
          </aside>
        </div>
      </section>

      <PageContainer>
        <section className="flex flex-col gap-4">
          <h2 className="section-title">How it works</h2>
          <ol className="grid gap-4 md:grid-cols-3">
            {steps.map((step, index) => (
              <li key={step.title} className="panel">
                <div className="flex items-center justify-between">
                  <step.Icon aria-hidden="true" className="h-6 w-6 text-royal" />
                  <span className="text-xs font-semibold tracking-wide text-saffron uppercase">Step {index + 1}</span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-navy">{step.title}</h3>
                <p className="mt-2 leading-6 text-muted">{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="section-title">Why it helps</h2>
          <ul className="grid gap-4 md:grid-cols-3">
            {reasons.map((reason) => (
              <li key={reason.title} className="panel">
                <reason.Icon aria-hidden="true" className="h-6 w-6 text-india" />
                <h3 className="mt-3 text-lg font-semibold text-navy">{reason.title}</h3>
                <p className="mt-2 leading-6 text-muted">{reason.text}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="section-title">Supported services</h2>
          <p className="text-muted">These names and document counts come from the database.</p>
          <Suspense fallback={<LoadingSkeleton label="Loading services" />}>
            <SupportedServices />
          </Suspense>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <article className="panel">
            <h2 className="text-xl font-semibold text-navy">Trust and privacy</h2>
            <p className="mt-2 text-muted">
              Sign-in uses your own account. Document names can be shown in English or Tamil. Files are
              not uploaded in this step. The Tamil Nadu emblem is shown for recognition only, and this
              site is not an official government service.
            </p>
          </article>
          <Disclaimer />
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">System status</h2>
          <SystemStatus />
        </section>
      </PageContainer>
    </>
  );
}
