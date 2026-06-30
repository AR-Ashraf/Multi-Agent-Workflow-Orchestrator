import Script from "next/script";

/**
 * GA4 / GTM loader (CLAUDE.md §11). Renders nothing unless an id is configured,
 * so local/dev builds ship no trackers. Cross-domain linker ties the journey
 * across devs-core.com → cadenza.devs-core.com into one attributed session; IP
 * anonymization keeps it privacy-respecting (§10).
 */
const GA_ID = process.env.NEXT_PUBLIC_GA_ID;
const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID;
const DOMAINS = ["devs-core.com", "cadenza.devs-core.com"];

export function Analytics() {
  return (
    <>
      {GA_ID ? (
        <>
          <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
          <Script id="ga4-init" strategy="afterInteractive">
            {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}
gtag('js',new Date());
gtag('config','${GA_ID}',{anonymize_ip:true,linker:{domains:${JSON.stringify(DOMAINS)}}});`}
          </Script>
        </>
      ) : null}

      {GTM_ID ? (
        <Script id="gtm-init" strategy="afterInteractive">
          {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});
var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';
j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${GTM_ID}');`}
        </Script>
      ) : null}
    </>
  );
}

/** GTM <noscript> fallback — render just inside <body>. */
export function GtmNoScript() {
  if (!GTM_ID) return null;
  return (
    <noscript>
      <iframe
        src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
        height="0"
        width="0"
        style={{ display: "none", visibility: "hidden" }}
        title="gtm"
      />
    </noscript>
  );
}
