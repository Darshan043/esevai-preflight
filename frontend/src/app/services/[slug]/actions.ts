"use server";

import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

function servicePath(slug: string): string {
  return `/services/${encodeURIComponent(slug)}`;
}

export async function startNewCheck(serviceId: string, slug: string): Promise<void> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    redirect(`/login?next=${servicePath(slug)}`);
  }

  const { data: row, error } = await supabase
    .from("applications")
    .insert({
      user_id: data.user.id,
      service_id: serviceId,
      status: "draft",
    })
    .select("id")
    .single();

  if (error || !row) {
    redirect(`${servicePath(slug)}?error=start`);
  }

  redirect(`/applications/${row.id}`);
}
