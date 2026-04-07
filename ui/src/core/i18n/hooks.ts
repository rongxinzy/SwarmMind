"use client";

// Simplified i18n for SwarmMind - returns Chinese translations

const translations = {
  clipboard: {
    copyToClipboard: "复制到剪贴板",
  },
  toolCalls: {
    searchForRelatedInfo: "搜索相关信息",
    searchOnWebFor: (query: string) => `搜索: ${query}`,
    searchForRelatedImages: "搜索相关图片",
    searchForRelatedImagesFor: (query: string) => `搜索图片: ${query}`,
    viewWebPage: "查看网页",
    listFolder: "列出文件夹",
    readFile: "读取文件",
    writeFile: "写入文件",
    executeCommand: "执行命令",
    needYourHelp: "需要您的帮助",
    writeTodos: "创建任务列表",
    useTool: (name: string) => `使用工具: ${name}`,
    moreSteps: (count: number) => `展开 ${count} 个步骤`,
    lessSteps: "收起",
  },
  subtasks: {
    executing: (count: number) => `正在执行 ${count} 个子任务`,
    in_progress: "进行中",
    completed: "已完成",
    failed: "失败",
  },
  common: {
    thinking: "思考",
    install: "安装",
    download: "下载",
  },
  inputBox: {
    createSkillPrompt: "创建技能",
  },
  uploads: {
    uploading: "上传中...",
  },
};

export function useI18n() {
  return {
    locale: "zh-CN" as const,
    t: translations,
    changeLocale: () => {},
  };
}
