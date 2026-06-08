import type { RenderActionResultProps, RenderFetcherResultProps } from '../ClueUIPlugin';
import ClueUIPlugin from '../ClueUIPlugin';

class ImagePlugin extends ClueUIPlugin {
  name = 'ImagePlugin';
  format = 'image';
  version = '1.0.0';
  author = 'Mr. Green';
  description = 'Renders images.';

  actionResult(props: RenderActionResultProps) {
    const { result, ...additionalProps } = props;

    let json = result.output;
    if (typeof json === 'string') {
      try {
        json = JSON.parse(json);
      } catch {
        // do nothing, just render the string as is
      }
    }
    return <img src={json.image} alt={json.alt} {...additionalProps} />;
  }

  fetcherResult(props: RenderFetcherResultProps) {
    const { result, ...additionalProps } = props;
    let json = result.data;
    if (typeof json === 'string') {
      try {
        json = JSON.parse(json);
      } catch {
        // do nothing, just render the string as is
      }
    }
    return <img src={json.image} alt={json.alt} {...additionalProps} />;
  }

  editorLanguage() {
    return 'json';
  }

  exampleInput() {
    return '{ "image": "/svg/dark/clue-icon2.svg", "alt": "Clue Logo" }';
  }

  documentation() {
    return `This plugin renders images. It can be used by specifying "image" as the format in the plugin configuration. The input should be a json object with an "image" property that is the URL of the image, and an optional "alt" property for the alt text of the image.`;
  }
}
export default ImagePlugin;
