import { createFileRoute } from "@tanstack/react-router";
import { KatanaProvider } from "@/lib/katana/store";
import { useIsMobile } from "@/hooks/use-mobile";
import { DeskSurface } from "@/components/katana/DeskSurface";
import { MobileSurface } from "@/components/katana/MobileSurface";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Katana MkII Control Surface" },
      {
        name: "description",
        content:
          "Touch-first control surface for the BOSS Katana MkII: channels, amp models, effects, drawable 10-band EQ and wah, built for a 9-inch amp-side screen and phones.",
      },
      { property: "og:title", content: "Katana MkII Control Surface" },
      {
        property: "og:description",
        content:
          "Every Katana MkII parameter on one screen — rotary amp selector, stomp tiles, drawable EQ curve and a swept wah treadle.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: RouteComponent,
});

function RouteComponent() {
  return (
    <KatanaProvider>
      <Surface />
    </KatanaProvider>
  );
}

/** Two separate screens — the phone layout and the 9-inch panel layout never mix. */
function Surface() {
  const isMobile = useIsMobile();
  return isMobile ? <MobileSurface /> : <DeskSurface />;
}
