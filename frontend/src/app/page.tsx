import { Suspense } from "react";

import { Disclaimer } from "@/components/Disclaimer";
import { HomeActions } from "@/components/HomeActions";
import { PageContainer } from "@/components/PageContainer";
import { SystemStatus } from "@/components/SystemStatus";

const steps = [
  { title: "Pick a service", text: "Choose the certificate or service you plan to apply for." },
  { title: "Upload your documents", text: "Add each document from the checklist. Upload opens in the next step." },
  { title: "Get your readiness report", text: "See what is ready and what still needs a fix before you apply." },
];

const reasons = [
  { title: "Fewer rejections", text: "Catch a missing or unreadable document before the counter does." },
  { title: "Saves a trip", text: "Check the list at home instead of travelling with the wrong papers." },
  { title: "Plain-language fixes", text: "Each problem is explained in everyday words, with a next step." },
];

export default function Home() {
  return (
    <PageContainer>
      <header className="flex flex-col gap-4">
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 sm:text-4xl">
          Check your documents before you apply
        </h1>
        <p className="max-w-2xl text-lg text-zinc-600">
          e-Sevai Pre-Flight helps you prepare a government application before you submit it.
        </p>
        <Suspense fallback={<p className="text-zinc-600">Loading account actions...</p>}>
          <HomeActions />
        </Suspense>
      </header>

      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-semibold text-zinc-900">How it works</h2>
        <ol className="grid gap-4 md:grid-cols-3">
          {steps.map((step, index) => (
            <li key={step.title} className="rounded-xl border border-zinc-200 bg-white p-5">
              <p className="text-sm font-medium text-zinc-500">Step {index + 1}</p>
              <h3 className="mt-2 text-lg font-semibold text-zinc-900">{step.title}</h3>
              <p className="mt-2 text-zinc-600">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-semibold text-zinc-900">Why it helps</h2>
        <ul className="grid gap-4 md:grid-cols-3">
          {reasons.map((reason) => (
            <li key={reason.title} className="rounded-xl border border-zinc-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-zinc-900">{reason.title}</h3>
              <p className="mt-2 text-zinc-600">{reason.text}</p>
            </li>
          ))}
        </ul>
      </section>

      <Disclaimer />

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">System status</h2>
        <SystemStatus />
      </section>
    </PageContainer>
  );
}
