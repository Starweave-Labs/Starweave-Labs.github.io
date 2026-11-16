# 星织实验室 · Starweave Labs

**汇聚灵感，共织作品。**

星织实验室的独立组织官网：<https://starweave-labs.github.io/>。

A collaborative lab weaving ideas into meaningful projects.

## 网站内容

- **共创理念**：伙伴平等、过程开放、认真完成。
- **探索方向**：产品界面、开发工具与 AI 协作；这些是探索方向，不是已完成的项目清单。
- **关联项目**：ZUVI 的简介、现有源码与文档入口。
- **参与共创**：从描述问题、Issue 讨论到小步提交与评审。

> ZUVI 仍位于 [`yeyouyuan/zuvi`](https://github.com/yeyouyuan/zuvi)，暂未迁入本组织。本网站不改变其仓库归属、文档地址、发行或安装方式。

## 技术与结构

原生 HTML 与 CSS，零构建依赖。页面内容不依赖 JavaScript；没有外部字体、统计脚本、第三方 CDN 或密钥配置。

```text
.
├── index.html                  # 官网首页
├── 404.html                    # 找不到页面时的导航
├── assets/
│   ├── styles.css              # 品牌与响应式样式
│   ├── constellation.svg       # 原创星点与织线图
│   ├── favicon.svg             # 品牌图标
│   ├── social-card.svg         # 品牌分享图源文件
│   └── social-card.png         # 1200 × 630 分享预览图
├── robots.txt
├── sitemap.xml
└── .github/workflows/pages.yml # GitHub Pages 部署
```

网页采用语义化结构，提供跳转到主要内容的入口、键盘焦点样式与减少动画偏好支持。品牌图形为原创静态 SVG，不是产品的交互界面。

## 本地预览

在仓库目录运行：

```sh
python3 -I -m http.server 4178 --bind 127.0.0.1 --directory .
```

打开 <http://127.0.0.1:4178/>。无需安装依赖或运行构建。

## 部署

仓库名必须保留为 `Starweave-Labs.github.io`，GitHub Pages 使用 **GitHub Actions** 作为部署源。站点发布在组织域名的根路径 `/`，不是 `/zuvi/`。

合并到 `main` 会自动运行 `.github/workflows/pages.yml`：

1. 检出源码并配置 Pages。
2. 将首页、404 页面、SEO 文件和 `assets/` 放入独立 `_site/` 目录。
3. 上传静态产物，通过 `github-pages` 环境部署。

GitHub 官方 Actions 固定到核验过的提交 SHA；部署任务只获得 `pages: write` 和 `id-token: write` 等必要权限。产物不包含 `.git/`、工作流、README 或其他仓库管理文件。

维护者可以在 [Actions 页面](https://github.com/Starweave-Labs/Starweave-Labs.github.io/actions) 检查部署状态。自定义域名和仓库迁移不属于当前配置。

## 如何参与

欢迎带着真实问题与具体建议来共创，代码、文档、设计和测试都很重要。

- 实验室官网、定位与方向的建议：使用[本仓库 Issues](https://github.com/Starweave-Labs/Starweave-Labs.github.io/issues)。
- ZUVI 产品问题：使用 [ZUVI Issues](https://github.com/yeyouyuan/zuvi/issues)。
- 较大的改动先讨论范围，再在独立分支提交 PR；说明改动目的、截图与验证方式。

发布前检查中文内容、外部链接、桌面与窄屏布局、键盘导航，以及关联项目的归属表述。每个项目的许可与贡献规则，以其各自仓库为准。
