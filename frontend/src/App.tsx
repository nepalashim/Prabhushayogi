import { ChatWidget } from "./components/ChatWidget";

// The widget is a self-positioned fixed-corner overlay (ChatWidget.tsx), so
// the "host page" here is deliberately empty - this stands in for whatever
// real page the widget gets embedded into later.
function App() {
  return (
    <div className="min-h-screen">
      <ChatWidget />
    </div>
  );
}

export default App;
