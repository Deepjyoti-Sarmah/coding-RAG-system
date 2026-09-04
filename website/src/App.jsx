import Nav from "./components/Nav";
import Hero from "./components/Hero";
import Quickstart from "./components/Quickstart";
import Pipeline from "./components/Pipeline";
import Thesis from "./components/Thesis";
import TerminalShowcase from "./components/TerminalShowcase";
import Benchmark from "./components/Benchmark";
import McpTools from "./components/McpTools";
import Languages from "./components/Languages";
import BigWordmark from "./components/BigWordmark";
import Footer from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-ultra font-sans text-white">
      <Nav />
      <main>
        <Hero />
        <Quickstart />
        <Pipeline />
        <Thesis />
        <TerminalShowcase />
        <Benchmark />
        <McpTools />
        <Languages />
        <BigWordmark />
      </main>
      <Footer />
    </div>
  );
}
