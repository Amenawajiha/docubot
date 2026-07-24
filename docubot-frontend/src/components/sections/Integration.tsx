import React from "react";
import { MessageSquare, ShoppingBag, Database, CreditCard, MessageCircle, BarChart, HeartHandshake, Share2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function Integration() {
  const integrations = [
    {
      name: "Slack",
      category: "Messaging",
      icon: <MessageCircle className="w-8 h-8 text-[#E01E5A]" />,
      color: "hover:border-[#E01E5A]/40 hover:shadow-[#E01E5A]/5",
      description: "Trigger automated messages and deploy help agents directly inside Slack channels.",
    },
    {
      name: "Salesforce",
      category: "CRM & Sales",
      icon: <Database className="w-8 h-8 text-[#00A1E0]" />,
      color: "hover:border-[#00A1E0]/40 hover:shadow-[#00A1E0]/5",
      description: "Sync lead records, conversations, and user data automatically with Salesforce Cloud.",
    },
    {
      name: "Shopify",
      category: "E-Commerce",
      icon: <ShoppingBag className="w-8 h-8 text-[#96BF48]" />,
      color: "hover:border-[#96BF48]/40 hover:shadow-[#96BF48]/5",
      description: "Enable checkout assistance, track packages, and process customer refunds seamlessly.",
    },
    {
      name: "Stripe",
      category: "Billing",
      icon: <CreditCard className="w-8 h-8 text-[#635BFF]" />,
      color: "hover:border-[#635BFF]/40 hover:shadow-[#635BFF]/5",
      description: "Retrieve invoices, verify subscription billing statuses, and process payment links.",
    },
    {
      name: "HubSpot",
      category: "CRM & Marketing",
      icon: <BarChart className="w-8 h-8 text-[#FF7A59]" />,
      color: "hover:border-[#FF7A59]/40 hover:shadow-[#FF7A59]/5",
      description: "Sync tickets, update contact lifecycle stages, and log interactions in CRM databases.",
    },
    {
      name: "Zendesk",
      category: "Customer Support",
      icon: <HeartHandshake className="w-8 h-8 text-[#03363D]" />,
      color: "hover:border-[#03363D]/40 hover:shadow-[#03363D]/5",
      description: "Handover complex chatbot conversations to live Zendesk support agents automatically.",
    },
    {
      name: "WhatsApp",
      category: "Messaging",
      icon: <MessageSquare className="w-8 h-8 text-[#25D366]" />,
      color: "hover:border-[#25D366]/40 hover:shadow-[#25D366]/5",
      description: "Automate mobile communication via the official WhatsApp Business cloud API.",
    },
    {
      name: "Discord",
      category: "Community",
      icon: <Share2 className="w-8 h-8 text-[#5865F2]" />,
      color: "hover:border-[#5865F2]/40 hover:shadow-[#5865F2]/5",
      description: "Support your gaming or developer community with context-aware auto-moderation.",
    },
  ];

  return (
    <section id="integrations" className="py-24 bg-slate-950/30 relative border-t border-white/5 scroll-mt-12">
      {/* Visual glowing radial background */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[300px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <Badge variant="primary" className="py-1 px-3">
            Connected Ecosystem
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Integrate with Your Everyday Tools
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Deploy OmniAI directly into your current tech ecosystem. No complicated coding required — connect using our native one-click plugins.
          </p>
        </div>

        {/* Integrations Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {integrations.map((item, idx) => (
            <Card
              key={idx}
              className={`flex flex-col h-full bg-slate-900/25 border-white/5 transition-all duration-300 group hover:-translate-y-1 hover:bg-slate-900/60 ${item.color} hover:shadow-[0_15px_30px_rgba(0,0,0,0.15)]`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-white/5 rounded-xl border border-white/10 group-hover:bg-white/10 transition-colors flex items-center justify-center">
                  {item.icon}
                </div>
                <Badge variant="outline" className="text-[9px] uppercase tracking-wide">
                  {item.category}
                </Badge>
              </div>
              <h3 className="text-base font-bold text-white mb-2 tracking-tight group-hover:text-white transition-colors">
                {item.name}
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed flex-1">
                {item.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
