// Simplified threads types for SwarmMind

export interface AgentThread {
  id: string;
  values: {
    artifacts?: string[];
  };
}
