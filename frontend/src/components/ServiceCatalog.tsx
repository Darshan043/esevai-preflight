"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import { useMemo, useState } from "react";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";

export type ServiceCardItem = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  documentCount: number;
  isVerified: boolean;
};

export function ServiceCatalog({ items }: { items: ServiceCardItem[] }) {
  const [query, setQuery] = useState("");
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return items;
    }
    return items.filter((item) => {
      const description = item.description?.toLowerCase() ?? "";
      return item.name.toLowerCase().includes(needle) || description.includes(needle);
    });
  }, [items, query]);

  return (
    <div className="flex flex-col gap-4">
      <div className="panel">
        <label className="block text-sm font-medium text-navy" htmlFor="service-search">
          Search services
          <input
            id="service-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type a service name"
            className="field"
          />
        </label>
      </div>
      {visible.length === 0 ? (
        <EmptyState title="No matching services" message="Try a different name, or clear the search." />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {visible.map((service) => (
            <li key={service.id}>
              <Card className="service-card flex h-full flex-col">
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-sky text-royal" aria-hidden="true">
                    <FileText className="h-5 w-5" />
                  </span>
                  <h2 className="text-xl font-semibold text-navy">{service.name}</h2>
                </div>
                {service.description ? <p className="mt-3 flex-1 leading-6 text-muted">{service.description}</p> : null}
                <p className="mt-3 inline-flex w-fit rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
                  {service.documentCount} required document{service.documentCount === 1 ? "" : "s"}
                </p>
                {service.isVerified ? (
                  <p className="mt-2 text-sm font-medium text-india">Verified</p>
                ) : (
                  <p className="mt-2 text-sm text-saffron" title="Draft list – confirm on the official portal">
                    Draft list – confirm on the official portal
                  </p>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/services/${service.slug}`} className="btn-primary">
                    Start document check
                  </Link>
                  <Link href={`/services/${service.slug}`} className="btn-secondary">
                    View details
                  </Link>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
