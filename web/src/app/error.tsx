"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main id="main" className="container section"><h1>Something didn’t load.</h1><p>Please try again. Your details have not been displayed in this error.</p><button className="button" onClick={reset}>Try again</button></main>;
}
