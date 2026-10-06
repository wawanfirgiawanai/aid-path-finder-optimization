import React, { useState } from 'react';
import '@/App.css';
import { AppProvider, useApp } from '@/contexts/AppContext';
import { Toaster } from 'sonner';
import Header from '@/components/Header';
import MapView from '@/components/MapView';
import LeftSidebar from '@/components/LeftSidebar';
import RightSidebar from '@/components/RightSidebar';
import Documentation from '@/components/Documentation';
import ExperimentsPanel from '@/components/ExperimentsPanel';

function AppContent() {
  const { theme } = useApp();
  const [showDocs, setShowDocs] = useState(false);
  const [showExperiments, setShowExperiments] = useState(false);
  return (
    <>
      <div className="app-layout">
        <Header onShowDocs={() => setShowDocs(true)} onShowExperiments={() => setShowExperiments(true)} />
        <div className="app-body">
          <LeftSidebar />
          <MapView />
          <RightSidebar />
        </div>
      </div>
      {showDocs && <Documentation onClose={() => setShowDocs(false)} />}
      <ExperimentsPanel open={showExperiments} onOpenChange={setShowExperiments} />
      <Toaster position="bottom-right" theme={theme} />
    </>
  );
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
