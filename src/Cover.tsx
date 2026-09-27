import React from 'react';
import {AbsoluteFill} from 'remotion';
import {config} from './config';
import {Footage, Grain, SafeBox, Scrim} from './components';
import {FONT, loadFonts} from './fonts';

loadFonts();
const C = config.colors;

// 숏츠 커버 (1080×1920 한 장)
export const Cover: React.FC = () => {
	const cv = config.cover;
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<Footage source={cv.source} from={cv.sourceFrom} dur={1} zoom={[1.28, 1.28]} />
			<Scrim top={0.75} bottom={0.9} />
			<SafeBox top={config.safe.top + 30}>
				<div style={{fontFamily: FONT.serif, fontWeight: 800, fontSize: 52, color: C.paper, marginBottom: 20}}>{cv.kicker}</div>
				{cv.title.map((t, i) => (
					<div key={i} style={{fontFamily: FONT.display, fontSize: 150, lineHeight: 1.1, whiteSpace: 'nowrap', color: i === cv.title.length - 1 ? C.pink : C.white, textShadow: '0 8px 40px rgba(0,0,0,.6)'}}>
						{t}
					</div>
				))}
			</SafeBox>
			<SafeBox top={config.height - config.safe.bottom - 130}>
				<div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 50, color: C.indigo, backgroundColor: C.pink, padding: '12px 36px 16px', borderRadius: 999}}>{cv.sub}</div>
			</SafeBox>
			<Grain />
		</AbsoluteFill>
	);
};
