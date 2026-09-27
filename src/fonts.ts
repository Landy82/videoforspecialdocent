import {continueRender, delayRender, staticFile} from 'remotion';

// 프로젝트에 포함된 OFL 폰트만 사용 (렌더링 환경에 따라 글자가 깨지지 않도록)
const faces: [string, string, string][] = [
	['Pretendard', 'fonts/Pretendard-Medium.otf', '500'],
	['Pretendard', 'fonts/Pretendard-Bold.otf', '700'],
	['Pretendard', 'fonts/Pretendard-ExtraBold.otf', '800'],
	['Pretendard', 'fonts/Pretendard-Black.otf', '900'],
	['BlackHanSans', 'fonts/black-han-sans-korean-400-normal.woff2', '400'],
	['Myeongjo', 'fonts/nanum-myeongjo-korean-800-normal.woff2', '800'],
	['Myeongjo', 'fonts/nanum-myeongjo-korean-400-normal.woff2', '400'],
];

export const FONT = {
	sans: 'Pretendard, sans-serif',
	display: 'BlackHanSans, Pretendard, sans-serif',
	serif: 'Myeongjo, serif',
};

let loaded = false;
export const loadFonts = () => {
	if (loaded) return;
	loaded = true;
	const handle = delayRender('fonts');
	Promise.all(
		faces.map(([family, file, weight]) => {
			const f = new FontFace(family, `url(${staticFile(file)})`, {weight});
			document.fonts.add(f);
			return f.load();
		}),
	)
		.then(() => continueRender(handle))
		.catch((e) => {
			console.error(e);
			continueRender(handle);
		});
};
