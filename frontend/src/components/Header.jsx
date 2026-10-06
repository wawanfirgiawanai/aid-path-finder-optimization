import React from 'react';
import { useApp } from '../contexts/AppContext';
import { t } from '../lib/translations';
import { Button } from './ui/button';
import { Sun, Moon, Globe, Route, FileText, FlaskConical } from 'lucide-react';

export default function Header({ onShowDocs, onShowExperiments }) {
  const { theme, toggleTheme, language, toggleLanguage } = useApp();
  return (
    <div className="app-header px-4 py-2.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-blue-600 flex items-center justify-center">
          <Route className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-tight leading-none" data-testid="app-title">OptiRoute</h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">{t(language, 'appSubtitle')}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <Button size="sm" onClick={onShowExperiments} className="h-8 px-3 text-xs gap-1.5" data-testid="paper-experiments-btn">
          <FlaskConical className="w-3.5 h-3.5" />Run Paper Experiments
        </Button>
        <Button variant="ghost" size="sm" onClick={onShowDocs} className="h-8 px-2 text-xs gap-1" data-testid="docs-btn">
          <FileText className="w-3.5 h-3.5" />Docs
        </Button>
        <Button variant="ghost" size="sm" onClick={toggleLanguage} data-testid="language-toggle" className="h-8 px-2 text-xs font-mono font-semibold gap-1">
          <Globe className="w-3.5 h-3.5" />{language.toUpperCase()}
        </Button>
        <Button variant="ghost" size="sm" onClick={toggleTheme} data-testid="theme-toggle" className="h-8 w-8 p-0">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}
