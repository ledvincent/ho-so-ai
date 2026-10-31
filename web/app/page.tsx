import Link from 'next/link';
export default function Home() {
  return <main className="landing"><p className="eyebrow">Your administrative companion</p><h1>Less paperwork.<br />A clearer next step.</h1><p>Prepare your information, review the document, and keep control of what you share.</p><Link className="button primary" href="/forms/demo">Prepare a form <span aria-hidden="true">→</span></Link><Link className="text-link" href="/portal">Open my dossier</Link><p className="demo-caption">Development scaffold. Official procedure data connects through Vincent’s reviewed contract.</p></main>;
}
