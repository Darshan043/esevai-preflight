export type HeaderAudience = "logged-out" | "citizen" | "admin";

export type HeaderLink = {
  href: string;
  label: string;
};

export function headerNavLinks(audience: HeaderAudience): HeaderLink[] {
  if (audience === "logged-out") {
    return [
      { href: "/", label: "Home" },
      { href: "/services", label: "Services" },
    ];
  }
  if (audience === "admin") {
    return [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/admin", label: "Admin" },
    ];
  }
  return [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/services", label: "Services" },
    { href: "/applications", label: "My applications" },
  ];
}

export function headerAudience(signedIn: boolean, isAdmin: boolean): HeaderAudience {
  if (!signedIn) {
    return "logged-out";
  }
  return isAdmin ? "admin" : "citizen";
}
