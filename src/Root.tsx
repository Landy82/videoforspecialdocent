import React from 'react';
import {Composition, Still} from 'remotion';
import {config, TOTAL_FRAMES} from './config';
import {Cover} from './Cover';
import {Main} from './Main';

export const Root: React.FC = () => (
	<>
		<Composition id="Shorts" component={Main} durationInFrames={TOTAL_FRAMES} fps={config.fps} width={config.width} height={config.height} />
		<Still id="Cover" component={Cover} width={config.width} height={config.height} />
	</>
);
