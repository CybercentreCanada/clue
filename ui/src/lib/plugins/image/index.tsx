import type { RenderActionResultProps, RenderFetcherResultProps } from '../ClueUIPlugin';
import ClueUIPlugin from '../ClueUIPlugin';
import { validateJsonData } from '../utils';

class ImagePlugin extends ClueUIPlugin {
  name = 'ImagePlugin';
  format = 'image';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders images.';

  actionResult(props: RenderActionResultProps) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { result, pluginId, ...additionalProps } = props;

    const json = validateJsonData(result.output);
    if (json !== null && json !== undefined) {
      const { image, alt } = json as { image: string; alt: string };
      return <img src={image} alt={alt ?? ''} {...additionalProps} />;
    }
    return null;
  }

  fetcherResult(props: RenderFetcherResultProps) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { result, fetcherId: _fetcherId, ...additionalProps } = props;
    const json = validateJsonData(result.data);
    if (json !== null && json !== undefined) {
      const { image, alt } = json as { image: string; alt: string };
      return <img src={image} alt={alt ?? ''} {...additionalProps} />;
    }
    return null;
  }

  editorLanguage() {
    return 'json';
  }

  exampleInput() {
    return JSON.stringify({ image: '/svg/dark/clue-icon2.svg', alt: 'Clue Logo' }, null, 2);
  }

  documentation() {
    return `This plugin renders images. It can be used by specifying "image" as the format in the plugin configuration. The input should be a json object with an "image" property that is the URL of the image, and an optional "alt" property for the alt text of the image.`;
  }
}
export default ImagePlugin;
