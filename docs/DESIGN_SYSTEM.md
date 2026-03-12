# Eluo Skill Hub — Design System

다른 프로젝트에서 동일한 디자인 언어를 재사용할 수 있도록 정리한 디자인 시스템 문서입니다.

---

## 1. Tech Stack

| 영역 | 기술 | 버전 |
|------|------|------|
| Framework | Next.js (App Router) | 16.1.6 |
| Language | TypeScript (strict, `any` 금지) | 5.x |
| Styling | Tailwind CSS v4 + OKLCH 색상 | 4.x |
| UI Components | Shadcn UI (Radix UI 기반) | - |
| Icons | lucide-react | ^0.576.0 |
| Animation | framer-motion + tw-animate-css | ^12.34.4 |
| Utilities | class-variance-authority, clsx, tailwind-merge | - |
| Font Loading | next/font/local | - |

---

## 2. Color System

### 2.1 Brand Colors

```css
--color-brand-yellow: #FEFE01;   /* 엘루오 브랜드 옐로 */
--color-brand-navy:   #00007F;   /* 엘루오 브랜드 네이비 */
--color-brand-light:  #F0F0F0;   /* 엘루오 브랜드 라이트 그레이 */
```

### 2.2 Semantic Color Tokens (Light Mode)

OKLCH 색상 공간을 사용하여 인지적으로 균일한 색상을 제공합니다.

| Token | OKLCH 값 | 용도 |
|-------|----------|------|
| `--background` | `oklch(1 0 0)` | 페이지 배경 (흰색) |
| `--foreground` | `oklch(0.145 0 0)` | 기본 텍스트 (거의 검정) |
| `--card` | `oklch(1 0 0)` | 카드 배경 |
| `--card-foreground` | `oklch(0.145 0 0)` | 카드 텍스트 |
| `--popover` | `oklch(1 0 0)` | 팝오버 배경 |
| `--popover-foreground` | `oklch(0.145 0 0)` | 팝오버 텍스트 |
| `--primary` | `oklch(0.205 0 0)` | 주요 버튼/강조 (다크 네이비) |
| `--primary-foreground` | `oklch(0.985 0 0)` | 주요 요소 위 텍스트 |
| `--secondary` | `oklch(0.97 0 0)` | 보조 배경 (오프화이트) |
| `--secondary-foreground` | `oklch(0.205 0 0)` | 보조 텍스트 |
| `--muted` | `oklch(0.97 0 0)` | 비활성/약한 배경 |
| `--muted-foreground` | `oklch(0.556 0 0)` | 보조 설명 텍스트 (미디엄 그레이) |
| `--accent` | `oklch(0.97 0 0)` | 강조 배경 |
| `--accent-foreground` | `oklch(0.205 0 0)` | 강조 텍스트 |
| `--destructive` | `oklch(0.577 0.245 27.325)` | 삭제/경고 (레드) |
| `--border` | `oklch(0.922 0 0)` | 기본 테두리 (라이트 그레이) |
| `--input` | `oklch(0.922 0 0)` | 입력 필드 테두리 |
| `--ring` | `oklch(0.708 0 0)` | 포커스 링 |

### 2.3 Semantic Color Tokens (Dark Mode)

`.dark` 클래스로 활성화됩니다.

| Token | OKLCH 값 | 변경 사항 |
|-------|----------|-----------|
| `--background` | `oklch(0.145 0 0)` | 다크 배경 |
| `--foreground` | `oklch(0.985 0 0)` | 밝은 텍스트 |
| `--card` | `oklch(0.205 0 0)` | 다크 카드 |
| `--primary` | `oklch(0.922 0 0)` | 밝은 주요 색상 (반전) |
| `--primary-foreground` | `oklch(0.205 0 0)` | 어두운 주요 텍스트 (반전) |
| `--secondary` | `oklch(0.269 0 0)` | 어두운 보조 배경 |
| `--muted` | `oklch(0.269 0 0)` | 어두운 비활성 배경 |
| `--muted-foreground` | `oklch(0.708 0 0)` | 밝은 보조 텍스트 |
| `--destructive` | `oklch(0.704 0.191 22.216)` | 밝은 레드 |
| `--border` | `oklch(1 0 0 / 10%)` | 투명도 기반 테두리 |
| `--input` | `oklch(1 0 0 / 15%)` | 투명도 기반 입력 테두리 |
| `--ring` | `oklch(0.556 0 0)` | 다크 포커스 링 |

### 2.4 다크 모드 구현

```css
/* Tailwind v4 커스텀 변형 */
@custom-variant dark (&:is(.dark *));

/* HTML에 .dark 클래스 토글로 전환 */
<html class="dark">
```

---

## 3. Typography

### 3.1 Font Families

| 토큰 | 폰트 | 용도 |
|------|------|------|
| `--font-sans` | Pretendard Variable (100–900) | 본문, 기본 UI |
| `--font-display` | Pretendard Variable | 디스플레이 텍스트 |
| `--font-eluo` | ELUO Face Variable | 브랜드 로고/타이틀 |

```typescript
// next/font/local 설정 (layout.tsx)
const pretendard = localFont({
  src: "./font/PretendardVariable.woff2",
  variable: "--font-pretendard",
  display: "swap",
  weight: "100 900",
});

const eluo = localFont({
  src: "./font/ELUOFACEVF.woff2",
  variable: "--font-eluo-face",
  display: "swap",
});
```

### 3.2 Typography Scale

| 용도 | Tailwind 클래스 | 크기 |
|------|----------------|------|
| 본문 (모바일) | `text-base` | 16px |
| 본문 (데스크탑) | `md:text-sm` | 14px |
| 작은 텍스트 | `text-sm` | 14px |
| 아주 작은 텍스트 | `text-xs` | 12px |
| 버튼 기본 | `text-sm` | 14px |
| 카드 제목 | `font-semibold` | weight 600 |
| 카드 설명 | `text-sm text-muted-foreground` | 14px, 그레이 |
| 라벨 | `text-sm font-medium` | 14px, weight 500 |
| 테이블 헤더 | `text-sm font-medium` | 14px, weight 500 |

### 3.3 Markdown (Notion 스타일) Typography

| 요소 | 크기 | 두께 | 행간 |
|------|------|------|------|
| H1 | `1.875rem` (30px) | 700 | 1.3 |
| H2 | `1.5rem` (24px) | 700 | 1.3 |
| H3 | `1.25rem` (20px) | 600 | 1.4 |
| 본문 | 상속 | 상속 | 1.7 |
| 코드 블록 | `0.875rem` (14px) | 상속 | 1.6 |
| 인라인 코드 | `0.85em` | 상속 | 상속 |

### 3.4 Monospace Font Stack

```css
font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
```

---

## 4. Spacing & Layout

### 4.1 Border Radius

| 토큰 | 값 | 계산 |
|------|-----|------|
| `--radius` | `0.625rem` (10px) | 기준 값 |
| `--radius-sm` | `0.375rem` (6px) | `--radius - 4px` |
| `--radius-md` | `0.5rem` (8px) | `--radius - 2px` |
| `--radius-lg` | `0.625rem` (10px) | `= --radius` |
| `--radius-xl` | `0.875rem` (14px) | `--radius + 4px` |

### 4.2 주요 Spacing 패턴

```
Button sizes:
  xs  → h-6  px-2  gap-1
  sm  → h-8  px-3  gap-1.5
  md  → h-9  px-4  py-2        (기본)
  lg  → h-10 px-6

Input → h-9 px-3 py-1
Textarea → min-h-16

Card:
  외부 패딩 → py-6 px-6
  내부 gap  → gap-6 (header/content/footer 사이)
  헤더 gap  → gap-2

Popover → w-72 (288px), p-4
```

### 4.3 Breakpoints (Tailwind v4 기본)

| Prefix | 최소 너비 |
|--------|-----------|
| `sm` | 640px |
| `md` | 768px |
| `lg` | 1024px |
| `xl` | 1280px |
| `2xl` | 1536px |

---

## 5. Component Library

### 5.1 Shadcn/ui Components

| 컴포넌트 | 파일 | 주요 기능 |
|----------|------|-----------|
| Button | `button.tsx` | 6 variants (default, destructive, outline, secondary, ghost, link), 5 sizes (xs, sm, default, lg, icon) |
| Card | `card.tsx` | Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter |
| Input | `input.tsx` | 텍스트 입력, 유효성 상태 지원 |
| Label | `label.tsx` | 폼 라벨, disabled/peer 지원 |
| Textarea | `textarea.tsx` | 멀티라인 입력, field-sizing-content |
| Select | `select.tsx` | 드롭다운, 아이템 인디케이터 |
| Dropdown Menu | `dropdown-menu.tsx` | 체크박스, 라디오, 구분선 지원 |
| Alert Dialog | `alert-dialog.tsx` | 모달 다이얼로그, 크기 variants (default, sm) |
| Popover | `popover.tsx` | 플로팅 팝오버, header/title/description 슬롯 |
| Switch | `switch.tsx` | 토글 스위치, 크기 variants (sm, default) |
| Table | `table.tsx` | 시맨틱 테이블 (header, body, footer, row, cell) |
| Calendar | `calendar.tsx` | 날짜 선택, 월/연도 드롭다운 |
| Chart | `chart.tsx` | Recharts 래퍼, 테마 지원 |
| Sonner (Toast) | `sonner.tsx` | 토스트 알림, 커스텀 아이콘 |

### 5.2 Custom Components

| 컴포넌트 | 파일 | 설명 |
|----------|------|------|
| Tag Chip | `tag-chip.tsx` | 해시태그 칩 |
| Interactive Globe | `interactive-globe.tsx` | 인터랙티브 3D 글로브 |
| Background Beams | `background-beams-with-collision.tsx` | 충돌 효과 배경 빔 |
| Notion Markdown | `NotionStyleMarkdown.tsx` | Notion 스타일 마크다운 렌더러 |
| Frontmatter Card | `FrontmatterCard.tsx` | 프론트매터 메타데이터 카드 |
| Cross Tab Logout | `CrossTabLogoutListener.tsx` | 탭 간 로그아웃 동기화 |

### 5.3 Button Variants

```tsx
// Variant 종류
default      → bg-primary text-primary-foreground shadow-xs
destructive  → bg-destructive text-white shadow-xs
outline      → border border-input bg-background shadow-xs
secondary    → bg-secondary text-secondary-foreground shadow-xs
ghost        → 투명 배경, hover 시 bg-accent
link         → 밑줄 텍스트, 높이 auto

// Size 종류
xs   → h-6  rounded-md px-2  (text-xs)
sm   → h-8  rounded-md px-3
md   → h-9  px-4 py-2        (기본)
lg   → h-10 rounded-md px-6
icon → size-9                 (정사각형)
```

---

## 6. Icons

### 6.1 사용 라이브러리

**lucide-react** (`^0.576.0`)

### 6.2 주요 아이콘 목록

| 아이콘 | 용도 |
|--------|------|
| `CheckIcon` | 선택 상태, 체크박스 |
| `ChevronDownIcon` | 드롭다운 표시 |
| `ChevronUpIcon` | 스크롤 위 |
| `ChevronRightIcon` | 서브메뉴 |
| `ChevronLeftIcon` | 달력 이전 |
| `CircleIcon` | 라디오 버튼 |
| `CircleCheckIcon` | 토스트 성공 |
| `InfoIcon` | 토스트 정보 |
| `TriangleAlertIcon` | 토스트 경고 |
| `OctagonXIcon` | 토스트 에러 |
| `Loader2Icon` | 로딩 스피너 (animate-spin) |

### 6.3 아이콘 크기 규칙

| 컨텍스트 | 클래스 | 크기 |
|----------|--------|------|
| 기본 | `size-4` | 16px |
| 버튼 xs | `size-3` | 12px |
| 토스트 | `size-4` | 16px |

---

## 7. Animation & Motion

### 7.1 CSS Animations

```css
/* 바텀 시트 슬라이드 업 */
@keyframes slide-up {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
.animate-slide-up {
  animation: slide-up 0.3s ease-out;
}
```

### 7.2 tw-animate-css 내장 애니메이션

| 애니메이션 | 지속 시간 | 용도 |
|------------|-----------|------|
| `slide-in-from-top-2` | 200ms | 드롭다운 진입 |
| `slide-in-from-bottom-2` | 200ms | 팝오버 진입 |
| `fade-in` / `fade-out` | 200ms | 오버레이 |
| `zoom-in-95` / `zoom-out-95` | 200ms | 모달 스케일 |
| `animate-spin` | - | 로딩 스피너 |

### 7.3 상태 기반 애니메이션

```tsx
// 드롭다운/팝오버 진입/퇴장
data-[state=open]:animate-in
data-[state=closed]:animate-out
data-[state=closed]:fade-out-0
data-[state=open]:fade-in-0

// 테이블 행 hover
transition-colors hover:bg-muted/50
```

### 7.4 Framer Motion

`framer-motion ^12.34.4` — 복잡한 페이지 전환 및 인터랙션 애니메이션에 사용.

---

## 8. Focus & Interaction States

### 8.1 포커스 링

```css
/* 기본 포커스 스타일 */
focus-visible:ring-[3px]
focus-visible:ring-ring/50
focus-visible:border-ring

/* 에러 상태 포커스 */
aria-invalid:ring-destructive/20
dark:aria-invalid:ring-destructive/40
```

### 8.2 Hover States

```css
/* 버튼 */
hover:bg-primary/90           /* default */
hover:bg-destructive/90       /* destructive */
hover:bg-accent               /* ghost */
dark:hover:bg-accent/50       /* ghost dark */

/* 입력 필드 */
hover:border-ring              /* 테두리 강조 */

/* 테이블 행 */
hover:bg-muted/50             /* 행 하이라이트 */
```

---

## 9. Shadows & Depth

| 클래스 | 용도 |
|--------|------|
| `shadow-xs` | 버튼, 입력 필드 |
| `shadow-sm` | 카드 |
| `shadow-md` | 드롭다운, 셀렉트 |
| `shadow-lg` | 모달, 다이얼로그 |
| `shadow-xl` | 툴팁 |

---

## 10. Z-Index Layers

| 값 | 용도 |
|----|------|
| `z-10` | 캘린더 포커스 날짜 |
| `z-50` | 드롭다운, 팝오버, 셀렉트, 모달 오버레이 |

---

## 11. Special Patterns

### 11.1 Glass Morphism

```css
.glass-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}
```

### 11.2 Scrollbar 숨기기

```css
.no-scrollbar::-webkit-scrollbar,
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.no-scrollbar,
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
```

### 11.3 Data Attributes 패턴

```tsx
data-slot="component-name"     // 시맨틱 네이밍
data-variant="variant-name"    // 변형 추적
data-size="size-name"          // 크기 추적
data-state="open|closed"       // 상태 관리
data-selected="true|false"     // 선택 상태
data-disabled="true|false"     // 비활성 상태
```

---

## 12. Notion Style Markdown Theme

마크다운 콘텐츠에 Notion 스타일을 적용합니다.

### 12.1 색상

| 요소 | 색상 |
|------|------|
| 기본 텍스트 | `#37352f` (다크 브라운) |
| 보조 텍스트 | `#9b9a97` (그레이 브라운) |
| 배경 | `#f7f6f3` (오프화이트) |
| 테두리 | `#e2e0dc` (라이트 베이지) |
| 코드 배경 | `#1e1e1e` (다크) |
| 코드 텍스트 | `#e4e4e7` (라이트 그레이) |
| 인라인 코드 | `#eb5757` (레드) on `rgba(135,131,120,0.15)` |

### 12.2 코드 Syntax Highlighting (github-dark 기반)

| 토큰 | 색상 |
|------|------|
| Keyword | `#ff7b72` |
| String | `#a5d6ff` |
| Number | `#79c0ff` |
| Built-in | `#ffa657` |
| Comment | `#8b949e` (italic) |
| Function | `#d2a8ff` |
| Variable | `#ffa657` |

---

## 13. Utility Functions

### 13.1 cn() — 클래스 병합 유틸리티

```typescript
// src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 13.2 CVA (Class Variance Authority)

컴포넌트 변형을 타입 안전하게 관리합니다.

```typescript
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva("base-classes", {
  variants: {
    variant: { default: "...", destructive: "..." },
    size: { default: "...", sm: "...", lg: "..." },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
});
```

---

## 14. 다른 프로젝트 적용 가이드

### 14.1 필수 패키지

```bash
npm install tailwindcss@^4 @tailwindcss/postcss@^4 @tailwindcss/typography tw-animate-css
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react radix-ui
npm install framer-motion  # 선택
```

### 14.2 최소 설정 파일

1. **globals.css** — 위 색상 토큰, 애니메이션, 유틸리티 클래스 복사
2. **layout.tsx** — `next/font/local`로 Pretendard + ELUO Face 폰트 등록
3. **src/lib/utils.ts** — `cn()` 유틸리티 함수 생성
4. **src/shared/ui/** — 필요한 Shadcn/ui 컴포넌트 복사 또는 `npx shadcn@latest add` 로 설치

### 14.3 Shadcn/ui 초기화

```bash
npx shadcn@latest init
npx shadcn@latest add button card input label textarea select dropdown-menu alert-dialog popover switch table calendar sonner
```

### 14.4 핵심 규칙

- `any` 타입 사용 금지 (TypeScript strict mode)
- OKLCH 색상 공간 사용으로 인지적 균일성 보장
- 시맨틱 토큰 기반 색상 시스템 (하드코딩 금지)
- `data-*` 속성으로 컴포넌트 상태 관리
- 포커스 링은 `ring-[3px] ring-ring/50` 패턴 일관 적용
