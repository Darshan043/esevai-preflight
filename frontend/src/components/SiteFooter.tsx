import { FooterAuth } from "@/components/FooterAuth";

export function SiteFooter() {
  return (
    <footer className="mt-auto bg-navy text-sky print:hidden">
      <div className="identity-bar" aria-hidden="true">
        <span className="bg-[#ff9933]" />
        <span className="bg-white" />
        <span className="bg-[#138808]" />
      </div>
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <p className="text-base font-semibold text-white">e-Sevai Pre-Flight</p>
          <p className="mt-2 max-w-md text-sm leading-6">
            An independent assistant for checking documents before you apply. This is not an official
            government service.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Pages</p>
          <ul className="mt-3 space-y-2 text-sm">
            <FooterAuth />
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Privacy</p>
          <p className="mt-3 text-sm leading-6">
            Your files stay on your account. Always confirm the latest requirements on the official
            Tamil Nadu e-Sevai portal.
          </p>
        </div>
      </div>
      <div className="border-t border-white/10">
        <p className="mx-auto w-full max-w-6xl px-4 py-4 text-xs leading-5 sm:px-6">
          The Tamil Nadu emblem is shown for recognition only. This site is not an official government
          service. Confirm every requirement on the official portal before you submit an application.
        </p>
      </div>
    </footer>
  );
}
