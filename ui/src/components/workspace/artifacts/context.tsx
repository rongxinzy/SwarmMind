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
  selectedArtifactUrl: string | null;
  isOpen: boolean;
  setArtifacts: (artifacts: Artifact[]) => void;
  selectArtifact: (artifact: Artifact | null) => void;
  selectArtifactByUrl: (url: string | null) => void;
  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  addArtifact: (artifact: Artifact) => void;
  removeArtifact: (id: string) => void;
  // Compatibility properties for message-group.tsx
  autoOpen: boolean;
  autoSelect: boolean;
  select: (artifactOrUrl: Artifact | string | null, byUrl?: boolean) => void;
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
  const [selectedArtifactUrl, setSelectedArtifactUrl] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const setArtifacts = useCallback((newArtifacts: Artifact[]) => {
    setArtifactsState(newArtifacts);
  }, []);

  const selectArtifact = useCallback((artifact: Artifact | null) => {
    setSelectedArtifact(artifact);
    if (artifact) {
      setSelectedArtifactUrl(null);
      setIsOpen(true);
    }
  }, []);

  const selectArtifactByUrl = useCallback((url: string | null) => {
    setSelectedArtifactUrl(url);
    if (url) {
      setSelectedArtifact(null);
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

  // Compatibility select function that handles both Artifact and URL string
  const select = useCallback((artifactOrUrl: Artifact | string | null, byUrl = false) => {
    if (artifactOrUrl === null) {
      setSelectedArtifact(null);
      setSelectedArtifactUrl(null);
    } else if (byUrl || typeof artifactOrUrl === 'string') {
      selectArtifactByUrl(typeof artifactOrUrl === 'string' ? artifactOrUrl : artifactOrUrl.id);
    } else {
      selectArtifact(artifactOrUrl);
    }
  }, [selectArtifact, selectArtifactByUrl]);

  return (
    <ArtifactsContext.Provider
      value={{
        artifacts,
        selectedArtifact,
        selectedArtifactUrl,
        isOpen,
        setArtifacts,
        selectArtifact,
        selectArtifactByUrl,
        setOpen,
        toggleOpen,
        addArtifact,
        removeArtifact,
        // Compatibility properties
        autoOpen: false,
        autoSelect: false,
        select,
      }}
    >
      {children}
    </ArtifactsContext.Provider>
  );
}
