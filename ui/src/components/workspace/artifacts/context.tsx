"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

// ============================================================================
// Types
// ============================================================================

export interface Artifact {
  id: string;
  path: string;
  filename: string;
  content?: string;
  mimeType?: string;
}

interface ArtifactsContextValue {
  artifacts: Artifact[];
  selectedArtifact: Artifact | null;
  isOpen: boolean;
  setArtifacts: (artifacts: Artifact[]) => void;
  selectArtifact: (artifact: Artifact | null) => void;
  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  addArtifact: (artifact: Artifact) => void;
  removeArtifact: (id: string) => void;
}

// ============================================================================
// Context
// ============================================================================

const ArtifactsContext = createContext<ArtifactsContextValue | null>(null);

export function useArtifacts() {
  const context = useContext(ArtifactsContext);
  if (!context) {
    throw new Error("useArtifacts must be used within ArtifactsProvider");
  }
  return context;
}

// ============================================================================
// Provider
// ============================================================================

interface ArtifactsProviderProps {
  children: ReactNode;
  initialArtifacts?: Artifact[];
}

export function ArtifactsProvider({
  children,
  initialArtifacts = [],
}: ArtifactsProviderProps) {
  const [artifacts, setArtifactsState] = useState<Artifact[]>(initialArtifacts);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const setArtifacts = useCallback((newArtifacts: Artifact[]) => {
    setArtifactsState(newArtifacts);
  }, []);

  const selectArtifact = useCallback((artifact: Artifact | null) => {
    setSelectedArtifact(artifact);
    if (artifact) {
      setIsOpen(true);
    }
  }, []);

  const setOpen = useCallback((open: boolean) => {
    setIsOpen(open);
  }, []);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const addArtifact = useCallback((artifact: Artifact) => {
    setArtifactsState((prev) => {
      const exists = prev.find((a) => a.id === artifact.id);
      if (exists) {
        return prev.map((a) => (a.id === artifact.id ? artifact : a));
      }
      return [...prev, artifact];
    });
  }, []);

  const removeArtifact = useCallback((id: string) => {
    setArtifactsState((prev) => prev.filter((a) => a.id !== id));
    setSelectedArtifact((prev) => (prev?.id === id ? null : prev));
  }, []);

  return (
    <ArtifactsContext.Provider
      value={{
        artifacts,
        selectedArtifact,
        isOpen,
        setArtifacts,
        selectArtifact,
        setOpen,
        toggleOpen,
        addArtifact,
        removeArtifact,
      }}
    >
      {children}
    </ArtifactsContext.Provider>
  );
}
