import Nav from "./components/Nav";
import Hero from "./components/Hero";
import TerminalShowcase from "./components/TerminalShowcase";
import PlatformCards from "./components/PlatformCards";
import FeatureGrid from "./components/FeatureGrid";
import DarkPanels from "./components/DarkPanels";
import StatsBar from "./components/StatsBar";
import Benchmark from "./components/Benchmark";
import Languages from "./components/Languages";
import CliReference from "./components/CliReference";
import BigWordmark from "./components/BigWordmark";
import CTA from "./components/CTA";
import Footer from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-paper font-sans text-ink">
      <Nav />
      <main>
        <Hero />
        <TerminalShowcase />
        <PlatformCards />
        <FeatureGrid />
        <DarkPanels />
        <StatsBar />
        <Benchmark />
        <Languages />
        <CliReference />
        <BigWordmark />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
