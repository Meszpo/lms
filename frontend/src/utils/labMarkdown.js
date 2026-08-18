/** Basic markdown renderer for lab descriptions (no task checkboxes). */
export function renderLabDescriptionMarkdown(text) {
	if (!text) return ''
	const lines = text.split('\n')
	const out = []
	let inUl = false
	let inOl = false

	function closeList() {
		if (inUl) { out.push('</ul>'); inUl = false }
		if (inOl) { out.push('</ol>'); inOl = false }
	}

	function inline(s) {
		return s
			.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
			.replace(/`([^`\n]+)`/g, '<code>$1</code>')
			.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
	}

	for (const line of lines) {
		const h1 = line.match(/^# (.+)$/)
		const h2 = line.match(/^## (.+)$/)
		const h3 = line.match(/^### (.+)$/)
		const ul = line.match(/^[*-] (.+)$/)
		const ol = line.match(/^\d+\. (.+)$/)
		const hr = line.match(/^---+$/)

		if (h1) { closeList(); out.push(`<h1>${inline(h1[1])}</h1>`) }
		else if (h2) { closeList(); out.push(`<h2>${inline(h2[1])}</h2>`) }
		else if (h3) { closeList(); out.push(`<h3>${inline(h3[1])}</h3>`) }
		else if (hr) { closeList(); out.push('<hr>') }
		else if (ul) {
			if (inOl) { out.push('</ol>'); inOl = false }
			if (!inUl) { out.push('<ul>'); inUl = true }
			out.push(`<li>${inline(ul[1])}</li>`)
		} else if (ol) {
			if (inUl) { out.push('</ul>'); inUl = false }
			if (!inOl) { out.push('<ol>'); inOl = true }
			out.push(`<li>${inline(ol[1])}</li>`)
		} else if (line.trim() === '') { closeList(); out.push('') }
		else { closeList(); out.push(`<p>${inline(line)}</p>`) }
	}
	closeList()
	return out.join('\n')
}

const CHIP_RE = /\+\[([^\]]+)\]\(([^)]+)\)/g
const CLIPBOARD_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>`

/** Render step instructions like LabWindow (with checkboxes and copy chips). */
export function renderStepInstructions(text, { stepIdx = 0, boxes = {}, resolve = (s) => s } = {}) {
	if (!text) return ''
	const resolved = resolve(text)
	const lines = resolved.split('\n')
	const out = []
	let inUl = false
	let inOl = false
	let inTaskUl = false
	let boxCounter = 0

	function closeList() {
		if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
		if (inUl) { out.push('</ul>'); inUl = false }
		if (inOl) { out.push('</ol>'); inOl = false }
	}

	function inlineMd(s) {
		return s
			.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
			.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>')
	}

	for (const line of lines) {
		const cb = line.match(/^- *\[([x ]?)\] +(.+)$/i)
		const h3 = !cb && line.match(/^### (.+)$/)
		const h2 = !cb && line.match(/^## (.+)$/)
		const h1 = !cb && line.match(/^# (.+)$/)
		const ul = !cb && line.match(/^[*-] (.+)$/)
		const ol = !cb && line.match(/^\d+\. (.+)$/)

		if (cb) {
			const bi = boxCounter++
			const key = `${stepIdx}:${bi}`
			const checked = boxes?.[key] ?? cb[1].toLowerCase() === 'x'
			if (inUl) { out.push('</ul>'); inUl = false }
			if (inOl) { out.push('</ol>'); inOl = false }
			if (!inTaskUl) { out.push('<ul class="task-list">'); inTaskUl = true }
			out.push(
				`<li class="task-item"><input type="checkbox" class="task-check" disabled${checked ? ' checked' : ''} />` +
				`<span class="task-text">${inlineMd(cb[2])}</span></li>`
			)
		} else if (h3) { closeList(); out.push(`<h5 class="md-h5">${inlineMd(h3[1])}</h5>`) }
		else if (h2) { closeList(); out.push(`<h4 class="md-h4">${inlineMd(h2[1])}</h4>`) }
		else if (h1) { closeList(); out.push(`<h3 class="md-h3">${inlineMd(h1[1])}</h3>`) }
		else if (ul) {
			if (inOl) { out.push('</ol>'); inOl = false }
			if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
			if (!inUl) { out.push('<ul class="md-ul">'); inUl = true }
			out.push(`<li>${inlineMd(ul[1])}</li>`)
		} else if (ol) {
			if (inUl) { out.push('</ul>'); inUl = false }
			if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
			if (!inOl) { out.push('<ol class="md-ol">'); inOl = true }
			out.push(`<li>${inlineMd(ol[1])}</li>`)
		} else if (line.trim() === '') {
			closeList()
			out.push('<div class="h-2"></div>')
		} else {
			closeList()
			out.push(`<p class="md-p">${inlineMd(line)}</p>`)
		}
	}
	closeList()

	return out.join('').replace(CHIP_RE, (_, label, value) => {
		const sv = value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		const sl = label.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		return `<span class="lms-copy-chip-preview" title="${sl}"><span class="lms-chip-icon">${CLIPBOARD_SVG}</span><span class="lms-chip-label">${sv}</span></span>`
	})
}

export const DESC_FMT_BUTTONS = [
	{ cmd: 'bold', label: 'B', title: __('Bold (**text**)') },
	{ cmd: 'italic', label: 'I', title: __('Italic (*text*)') },
	{ cmd: 'code', label: '</>', title: __('Inline code') },
	{ cmd: 'h2', label: 'H2', title: __('Heading 2 (## text)') },
	{ cmd: 'h3', label: 'H3', title: __('Heading 3 (### text)') },
	{ cmd: 'ul', label: __('• List'), title: __('Unordered list') },
	{ cmd: 'ol', label: __('1. List'), title: __('Ordered list') },
]

export const STEP_FMT_BUTTONS = [
	{ cmd: 'bold', label: 'B', title: __('Bold (**text**)') },
	{ cmd: 'italic', label: 'I', title: __('Italic (*text*)') },
	{ cmd: 'code', label: '</>', title: __('Inline code (`code`)') },
	{ cmd: 'ul', label: __('• List'), title: __('Unordered list (- item)') },
	{ cmd: 'ol', label: __('1. List'), title: __('Ordered list (1. item)') },
	{ cmd: 'check', label: __('☐ Checkbox'), title: __('Checkbox item (- [ ] item)') },
]

export function applyMarkdownFormat(textarea, text, cmd, onUpdate) {
	if (!textarea) return text
	const start = textarea.selectionStart
	const end = textarea.selectionEnd
	const sel = text.substring(start, end)
	let insert = ''
	let cursorOffset = 0

	if (cmd === 'bold') { insert = `**${sel || 'bold text'}**`; cursorOffset = sel ? insert.length : 2 }
	else if (cmd === 'italic') { insert = `*${sel || 'italic text'}*`; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'code') { insert = `\`${sel || 'code'}\``; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'h2') { insert = `## ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'h3') { insert = `### ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'ul') {
		insert = (sel || 'item').split('\n').map((l) => `- ${l}`).join('\n')
		cursorOffset = insert.length
	} else if (cmd === 'ol') {
		insert = (sel || 'item').split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n')
		cursorOffset = insert.length
	} else if (cmd === 'check') {
		insert = (sel || __('step to complete')).split('\n').map((l) => `- [ ] ${l}`).join('\n')
		cursorOffset = insert.length
	}

	const result = text.substring(0, start) + insert + text.substring(end)
	onUpdate?.(result, start + cursorOffset)
	return result
}
