---
name: second-world-poster
description: Create coherent multi-image marketing poster series from one selling point. Each poster is an independent image using the Second World visual system: preserve the real source photograph above and naturally extend an element from it into a symbolic second world below.
---

# Second World Poster — Universal Agent Skill

## Mission
Turn one selling point into a coherent series of independent marketing posters. The user chooses the number of images. Default to 3 when unspecified; recommend 3–4, but accept any reasonable count.

## Inputs and defaults
Use information already provided; ask only for essential missing details.
- Core selling point / campaign topic: required.
- Image count: user-defined; default 3.
- Target audience: infer if clear; otherwise state a reasonable assumption.
- Source photos: use uploaded photos when supplied.
- Format: vertical 3:4 by default.
- Language: follow the user; Chinese tasks default to Simplified Chinese.

If photos are supplied, map each poster to a source photo. Treat each photo independently. Never combine multiple source photos into a collage, grid, or single poster unless explicitly requested. If there are fewer photos than requested posters, ask whether photo reuse is acceptable; do not silently duplicate. If no photo is supplied, clarify whether the user wants concept-only artwork or will provide a real photo. Never present invented imagery as a real business location or photograph.

## Workflow

### 1. Commercial insight
Identify:
- What is offered?
- Who is the audience?
- What problem, desire, risk, or aspiration matters to them?
- What outcome does the selling point credibly provide?
- What evidence supports the claim?
- What action should the viewer take?

Translate product features into customer value without exaggerating. Consider the appropriate audience lens: business owner, HR/procurement, employee/end user, individual consumer, partner, or brand audience.

### 2. Plan the series
Create exactly the requested number of concepts. Every poster needs:
- A distinct communication angle.
- One primary message.
- A concise headline.
- Optional brief supporting copy.
- A source-photo mapping.
- A source-specific visual metaphor.
- A clear role in the series.

Potential angles include pain point, benefit, trust/proof, service experience, efficiency, emotional reassurance, long-term value, differentiation, and action. Select only angles that genuinely fit; do not force weak angles to fill the count.

Series rules:
- One central selling point across the series.
- Different sub-messages; no repeated headline or angle.
- Each poster must work independently when shared alone.
- Keep palette, typography, texture, and overall visual language consistent.
- Vary each poster's metaphor and composition.
- Never invent statistics, testimonials, awards, certifications, customer counts, guarantees, service times, or performance claims.

If the user asks for planning or approval, show the plan before image generation. If the user explicitly asks to generate directly, proceed with sensible assumptions.

### 3. Second World visual system
Default canvas: vertical 3:4.

Upper half (approximately 50%):
- Preserve the original photograph and real scene.
- Do not repaint, replace, beautify, redesign, or materially alter the photographed subject or setting.
- Only proportional crop/scale is allowed.
- Keep people, products, equipment, signage, and important details faithful.
- Do not add fabricated logos, signage, uniforms, equipment, or premises.

Lower half (approximately 50%):
- Warm ivory / natural paper-like background.
- Let a recognizable structure already present in the source photo cross the middle boundary and naturally extend into a symbolic “second world”.
- The extension must emerge from a real source element: path, shadow, reflection, contour, architecture, fabric fold, plant, hand gesture, machine component, light, or object edge.
- Shape the torn/transition edge according to the source image; never use a generic stock torn-paper divider.
- Use restrained black hand-drawn linework, paper cut-outs, or small fragments.
- Preserve generous negative space and clear headline hierarchy.
- The second world must express the commercial insight, not merely decorate the poster.

Hard prohibitions:
- No unrelated floating illustration or generic portal.
- No disconnected fantasy scenery.
- No dense ornaments, stickers, badges, or clutter.
- No repeated generic torn-paper template across all images.
- No altering the upper photo to make the concept easier.
- No merging source photos.
- No collage/contact sheet when separate images are requested.
- No fabricated brand marks or fake readable signage.

If the photo has no suitable structure to extend, use a subtle connection from an existing edge, silhouette, shadow, light, or object. If fidelity is still impossible, explain and request a better source photo rather than inventing a false scene.

### 4. Copy and claim integrity
Write for the audience, not the business's internal vocabulary.
- Headlines: short, specific, memorable; one idea per poster.
- Lead with customer value, not empty superlatives.
- Avoid unsupported absolutes such as “第一”, “最好”, “百分百”, “永久”, “零风险”, “保证”.
- Use measurable or comparative claims only when substantiated.
- For healthcare, finance, legal, education, and safety topics, use conservative, compliant wording; avoid guarantees and diagnosis/treatment claims.
- Keep supporting copy brief. If image generation may garble Chinese, leave a clean text-safe area and provide exact overlay copy separately.

### 5. Generate and deliver
- Generate each poster as a separate standalone image.
- Use the correct source photo for each concept.
- Maintain series consistency while varying each concept.
- Never claim an image was generated unless the image tool actually returned it.
- If image generation is unavailable, deliver production-ready prompts and state clearly that they are prompts, not rendered images.

## Output format
For a multi-image task, provide:
1. Series direction: selling point, audience, insight, count, shared visual identity.
2. Poster plan: for each image, role, headline, supporting copy, distinct angle, source photo, Second World concept.
3. Deliverables: separate images or separate prompts.
4. Quality check: count, independence, consistency, distinct angles, source-photo fidelity, and claim accuracy.

## Quality checklist
- [ ] Exact requested count.
- [ ] Each poster is a separate standalone image.
- [ ] One central selling point across the series.
- [ ] Distinct, non-repeated angles.
- [ ] Each image can be understood independently.
- [ ] Upper photo remains faithful and recognizable.
- [ ] Lower world grows naturally from the source photo.
- [ ] Transition edge is source-specific.
- [ ] Clean layout and sufficient negative space.
- [ ] Copy is accurate, legible, and concise.
- [ ] No unsupported claims or fabricated evidence.
- [ ] No accidental collage, grid, or merged photos.

## Example commands
- “围绕员工健康、企业未来，生成4张系列海报。”
- “这个产品的卖点是快速安装，做3张不同角度的海报。”
- “我上传了5张照片，每张分别设计一张海报，不要拼图。”
- “把这组海报扩展为6张，增加信任和服务体验角度。”
- “先策划系列方案，确认后再生成。”
