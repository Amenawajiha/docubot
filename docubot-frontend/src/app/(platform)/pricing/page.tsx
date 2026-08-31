import Header from "@/components/sections/Header";
import Pricing from "@/components/sections/Pricing";
import Footer from "@/components/sections/Footer";

export const metadata = {
  title: "Pricing Plans - SYNQDOC AI",
  description: "Simple, transparent pricing plans to scale your document AI chatbots.",
};

export default function PricingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground transition-colors duration-300">
      <Header />
      <main className="flex-1 pt-12">
        <Pricing />
      </main>
      <Footer />
    </div>
  );
}
