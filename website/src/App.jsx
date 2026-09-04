import Nav from "./components/Nav";
import Hero from "./components/Hero";
import Architecture from "./components/Architecture";
import Capabilities from "./components/Capabilities";
import Benchmark from "./components/Benchmark";
import Languages from "./components/Languages";
import CliReference from "./components/CliReference";
import CTA from "./components/CTA";
import Footer from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-paper font-sans text-ink">
      <Nav />
      <main>
        <Hero />
        <Architecture />
        <Capabilities />
        <Benchmark />
        <Languages />
        <CliReference />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
